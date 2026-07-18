"""Repository layer for church hierarchy."""

import logging
import secrets
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.crypto.encrypted_types import hmac_email, hmac_phone_digits
from app.common.id_utils import generate_id
from app.core.database import get_db
from app.modules.auth.auth_utils import get_password_hash
from app.modules.auth.db_models import UserDB
from app.modules.churches.acl_models import UserRoleAssignmentDB
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
from app.modules.churches.person_search import SEARCH_CANDIDATE_CAP, person_matches_query
from app.modules.churches.schemas import (
    BranchCreateRequest,
    BranchUpdateRequest,
    ServiceAssignmentCreateRequest,
    ServiceAssignmentUpdateRequest,
)
from app.modules.churches.seed_data import PASTOR_SERVICE_SLUGS
from app.modules.churches.slug_utils import church_slug
from app.modules.churches.visibility import VisibilityService
from app.modules.tenants.db_models import TenantMembershipDB

logger = logging.getLogger(__name__)


class ChurchRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

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
            logger.warning("search_persons: candidate set hit the %d-row safety cap; results may be incomplete for this scope", SEARCH_CANDIDATE_CAP)

        matches = [p for p in candidates if person_matches_query(first_name=p.first_name, last_name=p.last_name, email=p.email, phone=p.phone, query=trimmed)]
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
        can_grant_elevated_roles: bool,
    ) -> None:
        if person.user_id:
            return

        is_pastor = service_type and service_type.slug in PASTOR_SERVICE_SLUGS
        if not payload.createAccount:
            return

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
                is_active=not is_pastor,
                is_admin=False,
                created_at=datetime.now(UTC),
                is_email_verified=False,
            )
            self.db.add(user_db)
            await self.db.flush()

        person.user_id = user_db.id
        await self._ensure_tenant_membership(church.tenant_id, user_db.id)

        role_name = self._resolve_grant_role(payload, service_type, can_grant_elevated_roles)
        if not role_name:
            return

        roles_by_name = await ensure_acl_roles(self.db)
        role = roles_by_name.get(role_name)
        if not role:
            return

        scope = resolve_acl_scope(
            role_name,
            church_id=church.id,
            community_id=church.community_id,
            region_id=church.region_id,
        )
        if not scope:
            return

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
            return

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
        await self.db.flush()

    @staticmethod
    def _resolve_grant_role(
        payload: ServiceAssignmentCreateRequest,
        service_type: ServiceTypeDB | None,
        can_grant_elevated_roles: bool,
    ) -> str | None:
        """Return the ACL role to grant, or None. Rejects elevated grants."""
        role_name = payload.suggestedRole or (service_type.suggested_role if service_type else None)
        if not role_name or role_name not in PASTORAL_ROLE_NAMES:
            return None
        if role_name in ELEVATED_ROLE_NAMES and not can_grant_elevated_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Only admins may grant the '{role_name}' role",
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
        can_grant_elevated_roles: bool = False,
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

        # Reject an elevated role grant before anything is written.
        self._resolve_grant_role(payload, service_type, can_grant_elevated_roles)

        church = await self.ensure_church_access(scope_id)

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

        await self._maybe_create_user_and_acl(
            assignment.id,
            person,
            payload,
            service_type,
            church,
            can_grant_elevated_roles,
        )
        await self.db.commit()
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

    async def delete_service_assignment(self, scope_type: str, scope_id: str, assignment_id: str) -> bool:
        result = await self.db.execute(
            select(ServiceAssignmentDB).where(
                ServiceAssignmentDB.id == assignment_id,
                ServiceAssignmentDB.scope_type == scope_type,
                ServiceAssignmentDB.scope_id == scope_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if not assignment:
            return False
        await self.db.execute(delete(UserRoleAssignmentDB).where(UserRoleAssignmentDB.source_assignment_id == assignment_id))
        await self.db.delete(assignment)
        await self.db.commit()
        return True

    async def ensure_church_access(self, church_id: str) -> ChurchDB:
        church = await self.get_church_by_id(church_id)
        if not church:
            raise HTTPException(status_code=404, detail="Church not found")
        return church

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
            return {"name": None, "title": None, "phone": None, "email": None, "description": None}

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
