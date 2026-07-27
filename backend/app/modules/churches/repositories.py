"""Repository layer for church hierarchy."""

import logging
import secrets
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status
from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.crypto.encrypted_types import hmac_email, hmac_phone_digits
from app.common.id_utils import generate_id
from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.auth_utils import create_invite_token, get_password_hash
from app.modules.auth.db_models import UserDB
from app.modules.auth.models import User
from app.modules.churches.acl_seed import Permission
from app.modules.churches.acl_grant_rules import assert_can_assign_service_type, assert_can_grant_role
from app.modules.churches.acl_models import RoleDB, UserPermissionDB, UserRoleAssignmentDB
from app.modules.churches.acl_seed import (
    ELEVATED_ROLE_NAMES,
    PASTORAL_ROLE_NAMES,
    ensure_acl_roles,
    resolve_acl_scope,
)
from app.modules.churches.db_models import (
    BranchDB,
    ChurchDB,
    PersonDB,
    RegionDB,
    ServiceAssignmentDB,
    ServiceTypeDB,
)
from app.modules.churches.person_search import (
    SEARCH_CANDIDATE_CAP,
    person_matches_query,
)
from app.modules.churches.permission_service import PermissionService
from app.modules.churches.schemas import (
    AccountState,
    AccountStatus,
    BranchCreateRequest,
    BranchUpdateRequest,
    ServiceAssignmentCreateRequest,
    ServiceAssignmentUpdateRequest,
)
from app.modules.churches.slug_utils import church_slug
from app.modules.churches.visibility import VisibilityService
from app.modules.governance.audit_service import AclAuditService
from app.modules.governance.db_models import AclAuditAction
from app.modules.tenants.db_models import TenantMembershipDB

if TYPE_CHECKING:
    from app.modules.churches.permission_cache import PermissionCache

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InviteResult:
    """Concrete (non-Optional) values from invite_assignment_account — the ORM columns
    backing these are nullable, but at the point this is returned they were all just set."""

    user_id: str
    name: str
    email: str
    token: str
    invited_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class GrantedRole:
    """A role grant written as a side effect of creating a service assignment
    (_maybe_create_user_and_acl) — returned so the router can audit-log it (G8)."""

    user_id: str
    role_name: str


@dataclass(frozen=True)
class RevokedGrant:
    """A role grant removed because its source service assignment was deleted (§5.3) —
    returned so the router can audit-log one role.revoke entry per grant (G8)."""

    user_id: str
    role_name: str


@dataclass(frozen=True)
class DeleteAssignmentResult:
    deleted: bool
    revoked_roles: list[RevokedGrant]

    def __bool__(self) -> bool:
        """Preserves `if not await repo.delete_service_assignment(...)`-style call sites
        that predate the richer return type (audit logging, G8) needing revoked_roles."""
        return self.deleted


def _account_state_from_user(user_db: UserDB) -> AccountState:
    """Derive UI account status from raw columns (G3):
    - active: account is usable today
    - invited / expired: inactive, distinguished by whether the outstanding invite token
      is still within its TTL
    - none: inactive with no outstanding invite (never invited, or invited-and-accepted
      followed by a separate deactivation — not expected in this flow, but not an error)
    """
    if user_db.is_active:
        status: AccountStatus = "active"
    elif user_db.invite_token:
        now = datetime.now(UTC)
        expiry = user_db.invite_token_expiry
        # SQLite (unit tests) returns naive datetimes even for DateTime(timezone=True)
        # columns; Postgres (prod) returns tz-aware ones. Normalize before comparing.
        if expiry and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        status = "expired" if (expiry and expiry <= now) else "invited"
    else:
        status = "none"

    return AccountState(
        userId=user_db.id,
        status=status,
        invitedAt=user_db.invited_at,
        invitationExpiresAt=user_db.invite_token_expiry,
    )


class ChurchRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AclAuditService(db)

    async def get_church_by_id(self, church_id: str) -> ChurchDB | None:
        result = await self.db.execute(select(ChurchDB).where(ChurchDB.id == church_id))
        return result.scalar_one_or_none()

    async def list_regions(self) -> list[RegionDB]:
        result = await self.db.execute(select(RegionDB).order_by(RegionDB.name))
        return list(result.scalars().all())

    async def list_service_types(self) -> list[ServiceTypeDB]:
        result = await self.db.execute(select(ServiceTypeDB).order_by(ServiceTypeDB.sort_order))
        return list(result.scalars().all())

    async def get_service_type(self, service_type_id: str) -> ServiceTypeDB | None:
        result = await self.db.execute(select(ServiceTypeDB).where(ServiceTypeDB.id == service_type_id))
        return result.scalar_one_or_none()

    async def list_branches(self, church_id: str) -> list[BranchDB]:
        result = await self.db.execute(select(BranchDB).where(BranchDB.church_id == church_id).order_by(BranchDB.name))
        return list(result.scalars().all())

    async def create_branch(self, church_id: str, payload: BranchCreateRequest) -> BranchDB:
        slug = payload.slug or church_slug(payload.name)
        branch = BranchDB(
            id=generate_id(),
            church_id=church_id,
            name=payload.name,
            slug=slug,
            visibility=payload.visibility,
        )
        self.db.add(branch)
        await self.db.commit()
        await self.db.refresh(branch)
        return branch

    async def update_branch(self, church_id: str, branch_id: str, payload: BranchUpdateRequest) -> BranchDB | None:
        result = await self.db.execute(
            select(BranchDB).where(
                BranchDB.id == branch_id,
                BranchDB.church_id == church_id,
            )
        )
        branch = result.scalar_one_or_none()
        if not branch:
            return None
        if payload.name is not None:
            branch.name = payload.name
        if payload.slug is not None:
            branch.slug = payload.slug
        if payload.visibility is not None:
            branch.visibility = payload.visibility
        await self.db.commit()
        await self.db.refresh(branch)
        return branch

    async def delete_branch(self, church_id: str, branch_id: str) -> bool:
        result = await self.db.execute(
            select(BranchDB).where(
                BranchDB.id == branch_id,
                BranchDB.church_id == church_id,
            )
        )
        branch = result.scalar_one_or_none()
        if not branch:
            return False
        await self.db.delete(branch)
        await self.db.commit()
        return True

    async def search_persons(
        self,
        query: str,
        allowed_church_ids: set[str] | None = None,
        limit: int = 20,
    ) -> list[PersonDB]:
        """Search persons by name/phone/email, scoped to allowed churches.

        ``allowed_church_ids=None`` means unrestricted (admin/owner) — same
        convention as DirectoryRepository.get_allowed_church_ids. Any other
        caller (e.g. the /churches/persons/search autocomplete) must resolve
        and pass the caller's actual scope; otherwise this would leak contact
        data across tenants.

        first_name/last_name/email/phone are encrypted at rest, so matching
        happens in Python (person_matches_query) against a candidate set
        scoped in SQL by ACL only — see person_search.py for why.
        """
        trimmed = query.strip()
        if not trimmed:
            return []

        stmt = select(PersonDB)
        if allowed_church_ids is not None:
            stmt = stmt.where(
                PersonDB.id.in_(
                    select(ServiceAssignmentDB.person_id).where(
                        ServiceAssignmentDB.scope_type == "church",
                        ServiceAssignmentDB.scope_id.in_(allowed_church_ids),
                    )
                )
            )
        stmt = stmt.limit(SEARCH_CANDIDATE_CAP)
        result = await self.db.execute(stmt)
        candidates = result.scalars().all()
        if len(candidates) == SEARCH_CANDIDATE_CAP:
            logger.warning(
                "search_persons: candidate set hit the %d-row safety cap; results may be incomplete for this scope",
                SEARCH_CANDIDATE_CAP,
            )

        matches = [
            p
            for p in candidates
            if person_matches_query(
                first_name=p.first_name,
                last_name=p.last_name,
                email=p.email,
                phone=p.phone,
                query=trimmed,
            )
        ]
        return matches[:limit]

    async def get_person(self, person_id: str) -> PersonDB | None:
        result = await self.db.execute(select(PersonDB).where(PersonDB.id == person_id))
        return result.scalar_one_or_none()

    async def create_standalone_person(
        self,
        *,
        first_name: str | None,
        last_name: str | None,
        email: str | None,
        phone: str | None,
    ) -> str:
        """Create a person not (yet) linked to any church via a service assignment."""
        person = PersonDB(
            id=generate_id(),
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
        )
        self.db.add(person)
        await self.db.commit()
        return person.id

    async def find_person_by_email_or_phone(self, *, email: str | None, phone: str | None) -> tuple[PersonDB, str] | None:
        """Exact-match lookup for confident auto-matching (e.g. Google Contacts
        import), as opposed to `search_persons`'s broad autocomplete matching.

        Returns (person, matched_by) for the first exact hit, preferring email.
        email/phone are encrypted at rest, so exact matches go through the
        HMAC blind indices (email_bidx/phone_bidx) rather than comparing the
        columns directly — see app/common/crypto/encrypted_types.
        """
        if email:
            result = await self.db.execute(select(PersonDB).where(PersonDB.email_bidx == hmac_email(email)))
            person = result.scalars().first()
            if person:
                return person, "email"

        phone_bidx = hmac_phone_digits(phone)
        if phone_bidx:
            result = await self.db.execute(select(PersonDB).where(PersonDB.phone_bidx == phone_bidx))
            person = result.scalars().first()
            if person:
                return person, "phone"

        return None

    async def list_service_assignments(self, scope_type: str, scope_id: str) -> list[ServiceAssignmentDB]:
        result = await self.db.execute(
            select(ServiceAssignmentDB)
            .where(
                ServiceAssignmentDB.scope_type == scope_type,
                ServiceAssignmentDB.scope_id == scope_id,
            )
            .options(
                selectinload(ServiceAssignmentDB.person),
                selectinload(ServiceAssignmentDB.service_type),
            )
            .order_by(
                ServiceAssignmentDB.sort_order,
                ServiceAssignmentDB.created_at,
            )
        )
        return list(result.scalars().all())

    async def get_service_assignment(self, scope_type: str, scope_id: str, assignment_id: str) -> ServiceAssignmentDB | None:
        result = await self.db.execute(
            select(ServiceAssignmentDB)
            .where(
                ServiceAssignmentDB.id == assignment_id,
                ServiceAssignmentDB.scope_type == scope_type,
                ServiceAssignmentDB.scope_id == scope_id,
            )
            .options(
                selectinload(ServiceAssignmentDB.person),
                selectinload(ServiceAssignmentDB.service_type),
            )
        )
        return result.scalar_one_or_none()

    async def get_account_states(self, persons: Sequence[PersonDB]) -> dict[str, AccountState]:
        """Account state per person_id, for persons that have a linked account. Persons
        without a user_id are omitted — callers treat "not in dict" as no account (G3)."""
        user_ids = {p.user_id for p in persons if p.user_id}
        if not user_ids:
            return {}

        result = await self.db.execute(select(UserDB).where(UserDB.id.in_(user_ids)))
        users_by_id = {u.id: u for u in result.scalars().all()}

        states: dict[str, AccountState] = {}
        for person in persons:
            if not person.user_id:
                continue
            user_db = users_by_id.get(person.user_id)
            if not user_db:
                continue
            states[person.id] = _account_state_from_user(user_db)
        return states

    async def invite_assignment_account(
        self,
        assignment: ServiceAssignmentDB,
        *,
        actor: User,
    ) -> InviteResult:
        """Generate/overwrite an invite token for the account linked to this assignment's
        person. Idempotent: a second call for the same assignment silently invalidates the
        previous invite token by overwriting it.

        Raises HTTPException for preconditions the router can't check itself: no email on
        file, or no account created yet (§010 — invite never silently creates one)."""
        person = assignment.person
        if not person or not person.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Person has no email address on file",
            )
        if not person.user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Create an account for this person first",
            )

        result = await self.db.execute(select(UserDB).where(UserDB.id == person.user_id))
        user_db = result.scalar_one_or_none()
        if not user_db:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Linked account not found")

        token = create_invite_token(data={"sub": user_db.id})
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=settings.security.invite_token_expires_hours)
        user_db.invite_token = token
        user_db.invite_token_expiry = expires_at
        user_db.invited_at = now
        user_db.invited_by = actor.id

        await self.audit.record(
            actor=actor,
            action=AclAuditAction.INVITE_SENT,
            target_user_id=user_db.id,
            target_label=user_db.name,
            scope_type=assignment.scope_type,
            scope_id=assignment.scope_id,
        )

        await self.db.commit()
        await self.db.refresh(user_db)
        return InviteResult(
            user_id=user_db.id,
            name=user_db.name,
            email=person.email,
            token=token,
            invited_at=now,
            expires_at=expires_at,
        )

    async def _next_sort_order(self, scope_type: str, scope_id: str) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.max(ServiceAssignmentDB.sort_order), -1)).where(
                ServiceAssignmentDB.scope_type == scope_type,
                ServiceAssignmentDB.scope_id == scope_id,
            )
        )
        return int(result.scalar_one()) + 1

    async def _resolve_person(self, payload: ServiceAssignmentCreateRequest) -> PersonDB:
        if payload.personId:
            person = await self.get_person(payload.personId)
            if not person:
                raise HTTPException(status_code=404, detail="Person not found")
            return person

        person = PersonDB(
            id=generate_id(),
            first_name=payload.firstName,
            last_name=payload.lastName,
            email=payload.email,
            phone=payload.phone,
        )
        self.db.add(person)
        await self.db.flush()
        return person

    async def _maybe_create_user_and_acl(
        self,
        assignment_id: str,
        person: PersonDB,
        payload: ServiceAssignmentCreateRequest,
        service_type: ServiceTypeDB | None,
        church: ChurchDB,
        actor: User | None,
        permission_service: PermissionService | None,
    ) -> GrantedRole | None:
        """Create a user/ACL grant for the assigned person if requested. Returns the granted
        role (so callers can invalidate their cache entry and audit-log the grant), or None
        when nothing changed."""
        if person.user_id:
            return None

        if not payload.createAccount:
            return None

        if not person.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email required to create user account",
            )

        existing = await self.db.execute(select(UserDB).where(UserDB.email == person.email.lower().strip()))
        user_db = existing.scalar_one_or_none()
        if not user_db:
            full_name = " ".join(p for p in (person.first_name, person.last_name) if p).strip() or person.email
            user_db = UserDB(
                id=generate_id(),
                email=person.email.lower().strip(),
                name=full_name,
                hashed_password=get_password_hash(secrets.token_urlsafe(32)),
                # Always inactive at creation — nobody knows this random password. The
                # account is activated only by accepting a governance invite (G2), which
                # proves control of the inbox. Previously this was `not is_pastor`, so
                # non-pastor accounts looked "active" despite no one holding the password.
                is_active=False,
                is_admin=False,
                created_at=datetime.now(UTC),
                is_email_verified=False,
            )
            self.db.add(user_db)
            await self.db.flush()

        person.user_id = user_db.id
        await self._ensure_tenant_membership(church.tenant_id, user_db.id)

        role_name = None
        if actor and permission_service:
            role_name = await self._resolve_grant_role(
                payload,
                service_type,
                actor,
                permission_service,
                church,
            )
        elif payload.suggestedRole or (service_type.suggested_role if service_type else None):
            role_name = payload.suggestedRole or (service_type.suggested_role if service_type else None)
            if role_name and role_name not in PASTORAL_ROLE_NAMES:
                role_name = None
        if not role_name:
            return None

        roles_by_name = await ensure_acl_roles(self.db)
        role = roles_by_name.get(role_name)
        if not role:
            return None

        scope = resolve_acl_scope(
            role_name,
            church_id=church.id,
            community_id=church.community_id,
            region_id=church.region_id,
        )
        if not scope:
            return None

        scope_type, scope_id = scope
        existing_assignment = await self.db.execute(
            select(UserRoleAssignmentDB).where(
                UserRoleAssignmentDB.user_id == user_db.id,
                UserRoleAssignmentDB.role_id == role.id,
                UserRoleAssignmentDB.scope_type == scope_type,
                UserRoleAssignmentDB.scope_id == scope_id,
            )
        )
        if existing_assignment.scalar_one_or_none():
            return None

        self.db.add(
            UserRoleAssignmentDB(
                id=generate_id(),
                user_id=user_db.id,
                role_id=role.id,
                scope_type=scope_type,
                scope_id=scope_id,
                source_assignment_id=assignment_id,
            )
        )
        await self.audit.record(
            actor=actor,
            action=AclAuditAction.ROLE_GRANT,
            target_user_id=user_db.id,
            target_label=user_db.name,
            scope_type=scope_type,
            scope_id=scope_id,
            role_name=role_name,
            source="ui" if actor else "system",
        )
        await self.db.flush()
        return GrantedRole(user_id=user_db.id, role_name=role_name)

    async def _resolve_grant_role(
        self,
        payload: ServiceAssignmentCreateRequest,
        service_type: ServiceTypeDB | None,
        actor: User,
        permission_service: PermissionService,
        church: ChurchDB,
    ) -> str | None:
        """Return the ACL role to grant, or None. Rejects invalid grants."""
        if not payload.createAccount and payload.suggestedRole is None:
            return None
        role_name = payload.suggestedRole or (service_type.suggested_role if service_type else None)
        if not role_name or role_name not in PASTORAL_ROLE_NAMES:
            return None

        grant_scope = resolve_acl_scope(
            role_name,
            church_id=church.id,
            community_id=church.community_id,
            region_id=church.region_id,
        )
        if not grant_scope:
            if role_name in ELEVATED_ROLE_NAMES:
                grant_scope = ("community", church.community_id)
            else:
                grant_scope = ("church", church.id)

        await assert_can_grant_role(
            permission_service,
            actor,
            role_name,
            grant_scope,
            community_id=church.community_id,
        )
        return role_name

    async def _ensure_tenant_membership(self, tenant_id: str, user_id: str) -> None:
        result = await self.db.execute(
            select(TenantMembershipDB).where(
                TenantMembershipDB.tenant_id == tenant_id,
                TenantMembershipDB.user_id == user_id,
            )
        )
        if result.scalar_one_or_none():
            return

        self.db.add(
            TenantMembershipDB(
                tenant_id=tenant_id,
                user_id=user_id,
                role="member",
            )
        )
        await self.db.flush()

    async def create_service_assignment(
        self,
        scope_type: str,
        scope_id: str,
        payload: ServiceAssignmentCreateRequest,
        *,
        actor: User | None = None,
        permission_service: PermissionService | None = None,
    ) -> ServiceAssignmentDB:
        if not payload.serviceTypeId and not payload.customServiceName:
            raise HTTPException(
                status_code=400,
                detail="serviceTypeId or customServiceName required",
            )

        service_type = None
        if payload.serviceTypeId:
            service_type = await self.get_service_type(payload.serviceTypeId)
            if not service_type:
                raise HTTPException(status_code=404, detail="Service type not found")

        church = await self.ensure_church_access(scope_id)

        if actor and permission_service:
            await assert_can_assign_service_type(
                permission_service,
                actor,
                ("church", church.id),
                service_type,
                community_id=church.community_id,
            )

            if payload.createAccount or payload.suggestedRole is not None:
                await self._resolve_grant_role(payload, service_type, actor, permission_service, church)

        person = await self._resolve_person(payload)

        sort_order = payload.sortOrder
        if sort_order is None:
            sort_order = await self._next_sort_order(scope_type, scope_id)

        assignment = ServiceAssignmentDB(
            id=generate_id(),
            person_id=person.id,
            service_type_id=payload.serviceTypeId,
            custom_service_name=payload.customServiceName,
            description=payload.description,
            scope_type=scope_type,
            scope_id=scope_id,
            show_on_list=payload.showOnList,
            profile_visibility=payload.profileVisibility,
            phone_visibility=payload.phoneVisibility,
            email_visibility=payload.emailVisibility,
            sort_order=sort_order,
        )
        self.db.add(assignment)
        await self.db.flush()

        granted_role = await self._maybe_create_user_and_acl(
            assignment.id,
            person,
            payload,
            service_type,
            church,
            actor,
            permission_service,
        )
        await self.db.commit()
        if permission_service and granted_role:
            await permission_service.cache.invalidate_user(granted_role.user_id)
        await self.db.refresh(assignment)
        loaded = await self.db.execute(
            select(ServiceAssignmentDB)
            .where(ServiceAssignmentDB.id == assignment.id)
            .options(
                selectinload(ServiceAssignmentDB.person),
                selectinload(ServiceAssignmentDB.service_type),
            )
        )
        return loaded.scalar_one()

    async def update_service_assignment(
        self,
        scope_type: str,
        scope_id: str,
        assignment_id: str,
        payload: ServiceAssignmentUpdateRequest,
        *,
        actor: User | None = None,
        permission_service: PermissionService | None = None,
    ) -> ServiceAssignmentDB | None:
        result = await self.db.execute(
            select(ServiceAssignmentDB)
            .where(
                ServiceAssignmentDB.id == assignment_id,
                ServiceAssignmentDB.scope_type == scope_type,
                ServiceAssignmentDB.scope_id == scope_id,
            )
            .options(selectinload(ServiceAssignmentDB.person))
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            return None

        church = await self.ensure_church_access(scope_id)
        if actor and permission_service and payload.serviceTypeId is not None:
            old_type = await self.get_service_type(assignment.service_type_id) if assignment.service_type_id else None
            new_type = await self.get_service_type(payload.serviceTypeId)
            for service_type in (old_type, new_type):
                if service_type:
                    await assert_can_assign_service_type(
                        permission_service,
                        actor,
                        ("church", church.id),
                        service_type,
                        community_id=church.community_id,
                    )

        if payload.serviceTypeId is not None:
            assignment.service_type_id = payload.serviceTypeId
        if payload.customServiceName is not None:
            assignment.custom_service_name = payload.customServiceName
        if payload.description is not None:
            assignment.description = payload.description
        if payload.showOnList is not None:
            assignment.show_on_list = payload.showOnList
        if payload.profileVisibility is not None:
            assignment.profile_visibility = payload.profileVisibility
        if payload.phoneVisibility is not None:
            assignment.phone_visibility = payload.phoneVisibility
        if payload.emailVisibility is not None:
            assignment.email_visibility = payload.emailVisibility
        if payload.sortOrder is not None:
            assignment.sort_order = payload.sortOrder

        person = assignment.person
        if person:
            if payload.firstName is not None:
                person.first_name = payload.firstName
            if payload.lastName is not None:
                person.last_name = payload.lastName
            if payload.email is not None:
                person.email = payload.email
            if payload.phone is not None:
                person.phone = payload.phone
            person.updated_at = datetime.now(UTC)

        await self.db.commit()
        reloaded = await self.db.execute(
            select(ServiceAssignmentDB)
            .where(ServiceAssignmentDB.id == assignment_id)
            .options(
                selectinload(ServiceAssignmentDB.person),
                selectinload(ServiceAssignmentDB.service_type),
            )
        )
        return reloaded.scalar_one_or_none()

    async def delete_service_assignment(
        self,
        scope_type: str,
        scope_id: str,
        assignment_id: str,
        *,
        cache: "PermissionCache | None" = None,
        actor: User | None = None,
    ) -> DeleteAssignmentResult:
        result = await self.db.execute(
            select(ServiceAssignmentDB).where(
                ServiceAssignmentDB.id == assignment_id,
                ServiceAssignmentDB.scope_type == scope_type,
                ServiceAssignmentDB.scope_id == scope_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            return DeleteAssignmentResult(deleted=False, revoked_roles=[])

        affected_user_ids: set[str] = set()
        role_rows = await self.db.execute(
            select(UserRoleAssignmentDB.user_id, RoleDB.name, UserDB.name).join(RoleDB, RoleDB.id == UserRoleAssignmentDB.role_id).join(UserDB, UserDB.id == UserRoleAssignmentDB.user_id).where(UserRoleAssignmentDB.source_assignment_id == assignment_id)
        )
        role_rows_all = role_rows.all()
        revoked_roles = [RevokedGrant(user_id=row[0], role_name=row[1]) for row in role_rows_all]
        revoked_user_names = {row[0]: row[2] for row in role_rows_all}
        affected_user_ids.update(g.user_id for g in revoked_roles)
        perm_rows = await self.db.execute(select(UserPermissionDB.user_id).where(UserPermissionDB.source_assignment_id == assignment_id))
        affected_user_ids.update(row[0] for row in perm_rows.all())

        await self.db.execute(delete(UserPermissionDB).where(UserPermissionDB.source_assignment_id == assignment_id))
        await self.db.execute(delete(UserRoleAssignmentDB).where(UserRoleAssignmentDB.source_assignment_id == assignment_id))
        await self.db.delete(assignment)

        batch_id = generate_id()
        for grant in revoked_roles:
            await self.audit.record(
                actor=actor,
                action=AclAuditAction.ROLE_REVOKE,
                target_user_id=grant.user_id,
                target_label=revoked_user_names.get(grant.user_id, grant.user_id),
                scope_type=scope_type,
                scope_id=scope_id,
                role_name=grant.role_name,
                source="ui" if actor else "system",
                batch_id=batch_id,
            )

        await self.db.commit()

        if cache:
            for user_id in affected_user_ids:
                await cache.invalidate_user(user_id)

        return DeleteAssignmentResult(deleted=True, revoked_roles=revoked_roles)

    async def ensure_church_access(self, church_id: str) -> ChurchDB:
        church = await self.get_church_by_id(church_id)
        if not church:
            raise HTTPException(status_code=404, detail="Church not found")
        return church

    async def update_visibility(self, church_id: str, visibility: str) -> ChurchDB | None:
        church = await self.get_church_by_id(church_id)
        if not church:
            return None
        church.visibility = visibility
        await self.db.commit()
        await self.db.refresh(church)
        return church

    async def move_region(
        self,
        church_id: str,
        region_id: str,
        cache: "PermissionCache | None",
    ) -> ChurchDB | None:
        church = await self.get_church_by_id(church_id)
        if not church:
            return None
        region = await self.db.get(RegionDB, region_id)
        if not region:
            raise HTTPException(status_code=404, detail="Region not found")
        church.region_id = region_id
        await self.db.commit()
        await self.db.refresh(church)
        if cache:
            await cache.bump_epoch()
        return church

    async def resolve_create_region(
        self,
        actor: User,
        permission_service: PermissionService,
        requested_region_id: str | None,
    ) -> tuple[str | None, str | None]:
        warning: str | None = None
        if actor.isAdmin or actor.isOwner:
            return requested_region_id, ("Church created without region — assign a region for regional bishop access" if not requested_region_id else None)

        allowed_regions = await permission_service.allowed_church_ids(actor, Permission.CHURCH_CREATE.value)
        _ = allowed_regions

        regions = await self.list_regions()
        for region in regions:
            if await permission_service.resolve(
                actor,
                Permission.CHURCH_CREATE,
                ("region", region.id),
            ):
                if requested_region_id and requested_region_id != region.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Regional bishops may only create churches in their own region",
                    )
                return region.id, None

        if await permission_service.has_anywhere(actor, Permission.CHURCH_CREATE):
            return requested_region_id, warning

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    async def list_public_card_assignments(self, church_id: str) -> list[ServiceAssignmentDB]:
        result = await self.db.execute(
            select(ServiceAssignmentDB)
            .outerjoin(ServiceAssignmentDB.service_type)
            .where(
                ServiceAssignmentDB.scope_type == "church",
                ServiceAssignmentDB.scope_id == church_id,
                ServiceAssignmentDB.show_on_list.is_(True),
            )
            .options(
                selectinload(ServiceAssignmentDB.person),
                selectinload(ServiceAssignmentDB.service_type),
            )
            .order_by(
                ServiceAssignmentDB.sort_order,
                ServiceAssignmentDB.created_at,
            )
        )
        return list(result.scalars().all())

    async def list_public_card_assignments_for_churches(self, church_ids: Sequence[str]) -> dict[str, list[ServiceAssignmentDB]]:
        """Public card assignments for many churches at once, keyed by church id."""
        if not church_ids:
            return {}
        result = await self.db.execute(
            select(ServiceAssignmentDB)
            .outerjoin(ServiceAssignmentDB.service_type)
            .where(
                ServiceAssignmentDB.scope_type == "church",
                ServiceAssignmentDB.scope_id.in_(church_ids),
                ServiceAssignmentDB.show_on_list.is_(True),
            )
            .options(
                selectinload(ServiceAssignmentDB.person),
                selectinload(ServiceAssignmentDB.service_type),
            )
            .order_by(
                ServiceAssignmentDB.sort_order,
                ServiceAssignmentDB.created_at,
            )
        )
        grouped: dict[str, list[ServiceAssignmentDB]] = defaultdict(list)
        for assignment in result.scalars():
            grouped[assignment.scope_id].append(assignment)
        return grouped

    async def count_service_assignments_for_churches(self, church_ids: Sequence[str]) -> dict[str, int]:
        """Count all service assignments (contact persons) per church, regardless of visibility."""
        if not church_ids:
            return {}
        stmt = (
            select(ServiceAssignmentDB.scope_id, func.count(ServiceAssignmentDB.id))
            .where(
                ServiceAssignmentDB.scope_type == "church",
                ServiceAssignmentDB.scope_id.in_(church_ids),
            )
            .group_by(ServiceAssignmentDB.scope_id)
        )
        result = await self.db.execute(stmt)
        counts: dict[str, int] = {}
        for scope_id, count in result.all():
            counts[scope_id] = count
        return counts

    async def get_contact_info_flags_for_churches(
        self,
        church_ids: Sequence[str],
    ) -> dict[str, dict[str, bool]]:
        """For each church, whether any assigned person has an email and/or phone set."""
        if not church_ids:
            return {}
        # MAX(CASE ...) instead of the Postgres-only bool_or, so this also runs
        # against the SQLite engine used by the integration test suite.
        stmt = (
            select(
                ServiceAssignmentDB.scope_id,
                func.max(case((PersonDB.email.is_not(None), 1), else_=0)),
                func.max(case((PersonDB.phone.is_not(None), 1), else_=0)),
            )
            .join(PersonDB, ServiceAssignmentDB.person_id == PersonDB.id)
            .where(
                ServiceAssignmentDB.scope_type == "church",
                ServiceAssignmentDB.scope_id.in_(church_ids),
            )
            .group_by(ServiceAssignmentDB.scope_id)
        )
        result = await self.db.execute(stmt)
        flags: dict[str, dict[str, bool]] = {}
        for scope_id, has_email, has_phone in result.all():
            flags[scope_id] = {
                "has_email": bool(has_email),
                "has_phone": bool(has_phone),
            }
        return flags

    async def list_public_branches_for_churches(self, church_ids: Sequence[str]) -> dict[str, list[BranchDB]]:
        """Publicly visible branches for many churches at once, keyed by church id."""
        if not church_ids:
            return {}
        result = await self.db.execute(
            select(BranchDB)
            .where(
                BranchDB.church_id.in_(church_ids),
                BranchDB.visibility == "public",
            )
            .order_by(BranchDB.name)
        )
        grouped: dict[str, list[BranchDB]] = defaultdict(list)
        for branch in result.scalars():
            grouped[branch.church_id].append(branch)
        return grouped

    def to_public_card_contact(
        self,
        assignment: ServiceAssignmentDB,
        *,
        is_authenticated: bool,
        has_pastoral_access: bool,
        bypass_field_visibility: bool = False,
    ) -> dict[str, str | None]:
        person = assignment.person
        if not person:
            return {
                "name": None,
                "title": None,
                "phone": None,
                "email": None,
                "description": None,
            }

        name = " ".join(part for part in (person.first_name, person.last_name) if part).strip()
        service_type = assignment.service_type
        title = service_type.name if service_type else assignment.custom_service_name
        if bypass_field_visibility:
            return {
                "name": name or None,
                "title": title,
                "phone": person.phone,
                "email": person.email,
                "description": assignment.description,
                "profile_visibility": assignment.profile_visibility,
                "phone_visibility": assignment.phone_visibility,
                "email_visibility": assignment.email_visibility,
            }

        contact_fields = self.filter_assignment_contact(
            assignment,
            is_authenticated=is_authenticated,
            has_pastoral_access=has_pastoral_access,
        )
        return {
            "name": name or None,
            "title": title,
            "phone": contact_fields["phone"],
            "email": contact_fields["email"],
            "description": assignment.description,
        }

    def profile_contacts_for_viewer(
        self,
        assignments: list[ServiceAssignmentDB],
        *,
        is_authenticated: bool,
        has_pastoral_access: bool,
        can_manage: bool,
    ) -> tuple[list[dict[str, str | None]], list[dict[str, str | None]]]:
        visible: list[dict[str, str | None]] = []
        hidden: list[dict[str, str | None]] = []

        for assignment in assignments:
            if assignment.profile_visibility == "hidden":
                if can_manage:
                    hidden.append(
                        self.to_public_card_contact(
                            assignment,
                            is_authenticated=True,
                            has_pastoral_access=True,
                            bypass_field_visibility=True,
                        )
                    )
                continue

            if not VisibilityService.can_view(
                assignment.profile_visibility,
                is_authenticated=is_authenticated,
                has_pastoral_access=has_pastoral_access,
            ):
                continue

            visible.append(
                self.to_public_card_contact(
                    assignment,
                    is_authenticated=is_authenticated,
                    has_pastoral_access=has_pastoral_access,
                    bypass_field_visibility=can_manage,
                )
            )

        return visible, hidden

    def filter_assignment_contact(
        self,
        assignment: ServiceAssignmentDB,
        *,
        is_authenticated: bool,
        has_pastoral_access: bool,
    ) -> dict[str, str | None]:
        person = assignment.person
        if not person:
            return {"phone": None, "email": None}

        return {
            "phone": VisibilityService.filter_contact_field(
                person.phone,
                assignment.phone_visibility,
                is_authenticated=is_authenticated,
                has_pastoral_access=has_pastoral_access,
            ),
            "email": VisibilityService.filter_contact_field(
                person.email,
                assignment.email_visibility,
                is_authenticated=is_authenticated,
                has_pastoral_access=has_pastoral_access,
            ),
        }


def get_church_repository(db: AsyncSession = Depends(get_db)) -> ChurchRepository:
    return ChurchRepository(db)
