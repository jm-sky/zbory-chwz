"""Repository layer for the people directory (email export + person browser) module.

See docs/plans/2026-07-09--mailing-lists.md.
"""

import logging

from fastapi import Depends
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.churches.acl_models import UserRoleAssignmentDB
from app.modules.churches.db_models import (
    ChurchDB,
    PersonDB,
    RegionDB,
    ServiceAssignmentDB,
    ServiceTypeDB,
)
from app.modules.churches.person_search import SEARCH_CANDIDATE_CAP, person_matches_query
from app.modules.directory.db_models import PersonChangeLogDB
from app.modules.directory.schemas import PersonUpdateRequest
from app.modules.groups.db_models import PeopleGroupDB, PeopleGroupMembershipDB

logger = logging.getLogger(__name__)

# (kind, label, context) — context is the church name for a service affiliation, None for a group.
Affiliation = tuple[str, str, str | None]


class DirectoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_allowed_church_ids(self, user: User) -> set[str] | None:
        """Church ids the user may access contacts from.

        ``None`` means unrestricted (admin/owner). An empty set means the
        user holds no ACL role at all and must be denied access.
        """
        if user.isAdmin or user.isOwner:
            return None

        result = await self.db.execute(select(UserRoleAssignmentDB.scope_type, UserRoleAssignmentDB.scope_id).where(UserRoleAssignmentDB.user_id == user.id))
        rows = result.all()
        if not rows:
            return set()

        church_ids: set[str] = set()
        region_ids: set[str] = set()
        community_ids: set[str] = set()
        for scope_type, scope_id in rows:
            if scope_type == "church":
                church_ids.add(scope_id)
            elif scope_type == "region":
                region_ids.add(scope_id)
            elif scope_type == "community":
                community_ids.add(scope_id)

        if region_ids or community_ids:
            conditions = []
            if region_ids:
                conditions.append(ChurchDB.region_id.in_(region_ids))
            if community_ids:
                conditions.append(ChurchDB.community_id.in_(community_ids))
            wider = await self.db.execute(select(ChurchDB.id).where(or_(*conditions)))
            church_ids.update(row[0] for row in wider.all())

        return church_ids

    async def list_available_regions(self, allowed_church_ids: set[str] | None) -> list[RegionDB]:
        stmt = select(RegionDB)
        if allowed_church_ids is not None:
            stmt = stmt.where(
                RegionDB.id.in_(
                    select(ChurchDB.region_id).where(
                        ChurchDB.id.in_(allowed_church_ids),
                        ChurchDB.region_id.isnot(None),
                    )
                )
            )
        stmt = stmt.order_by(RegionDB.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_service_types(self) -> list[ServiceTypeDB]:
        result = await self.db.execute(select(ServiceTypeDB).where(ServiceTypeDB.scope_type == "church").order_by(ServiceTypeDB.sort_order))
        return list(result.scalars().all())

    async def export_persons(
        self,
        allowed_church_ids: set[str] | None,
        *,
        region_ids: list[str],
        service_type_ids: list[str],
        group_ids: list[str],
    ) -> list[PersonDB]:
        # email is encrypted at rest, so a blank string no longer compares
        # equal to "" in SQL (ciphertext of "" isn't the literal empty
        # string) — writers normalize blank e-mails to None (see the
        # migration and PersonDB write sites), so isnot(None) alone is
        # sufficient here.
        stmt = select(PersonDB).where(PersonDB.email.isnot(None))

        if allowed_church_ids is not None:
            scoped_subq = select(ServiceAssignmentDB.person_id).where(
                ServiceAssignmentDB.scope_type == "church",
                ServiceAssignmentDB.scope_id.in_(allowed_church_ids),
            )
            stmt = stmt.where(PersonDB.id.in_(scoped_subq))

        if region_ids or service_type_ids:
            assignment_subq = select(ServiceAssignmentDB.person_id).join(ChurchDB, ChurchDB.id == ServiceAssignmentDB.scope_id).where(ServiceAssignmentDB.scope_type == "church")
            if region_ids:
                assignment_subq = assignment_subq.where(ChurchDB.region_id.in_(region_ids))
            if service_type_ids:
                assignment_subq = assignment_subq.where(ServiceAssignmentDB.service_type_id.in_(service_type_ids))
            stmt = stmt.where(PersonDB.id.in_(assignment_subq))

        if group_ids:
            membership_subq = select(PeopleGroupMembershipDB.person_id).where(
                PeopleGroupMembershipDB.group_id.in_(group_ids),
                PeopleGroupMembershipDB.left_at.is_(None),
            )
            stmt = stmt.where(PersonDB.id.in_(membership_subq))

        # first_name/last_name are encrypted at rest — sorting ciphertext in
        # SQL would produce a meaningless order, so sort in Python instead.
        result = await self.db.execute(stmt)
        persons = list(result.scalars().all())
        persons.sort(key=lambda p: ((p.first_name or "").lower(), (p.last_name or "").lower()))
        return persons

    # -- Person browser -----------------------------------------------------

    async def list_persons(self, allowed_church_ids: set[str] | None, *, query: str | None = None) -> list[PersonDB]:
        """List/search persons, scoped to allowed churches.

        first_name/last_name/email/phone are encrypted at rest, so matching
        and sorting happen in Python against a decrypted candidate set scoped
        in SQL by ACL only — see churches/person_search.py for why.
        """
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
        candidates = list(result.scalars().all())
        if len(candidates) == SEARCH_CANDIDATE_CAP:
            logger.warning("list_persons: candidate set hit the %d-row safety cap; results may be incomplete for this scope", SEARCH_CANDIDATE_CAP)

        trimmed = query.strip() if query else ""
        if trimmed:
            candidates = [p for p in candidates if person_matches_query(first_name=p.first_name, last_name=p.last_name, email=p.email, phone=p.phone, query=trimmed)]

        candidates.sort(key=lambda p: ((p.first_name or "").lower(), (p.last_name or "").lower()))
        return candidates[:200]

    async def get_person(self, person_id: str) -> PersonDB | None:
        result = await self.db.execute(select(PersonDB).where(PersonDB.id == person_id))
        return result.scalar_one_or_none()

    async def person_in_scope(self, person_id: str, allowed_church_ids: set[str] | None) -> bool:
        if allowed_church_ids is None:
            return await self.get_person(person_id) is not None
        result = await self.db.execute(
            select(ServiceAssignmentDB.id)
            .where(
                ServiceAssignmentDB.person_id == person_id,
                ServiceAssignmentDB.scope_type == "church",
                ServiceAssignmentDB.scope_id.in_(allowed_church_ids),
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_affiliations(self, person_ids: list[str]) -> dict[str, list[Affiliation]]:
        affiliations: dict[str, list[Affiliation]] = {pid: [] for pid in person_ids}
        if not person_ids:
            return affiliations

        assignment_rows = await self.db.execute(
            select(
                ServiceAssignmentDB.person_id,
                ServiceAssignmentDB.custom_service_name,
                ServiceTypeDB.name,
                ChurchDB.name,
            )
            .outerjoin(ServiceTypeDB, ServiceTypeDB.id == ServiceAssignmentDB.service_type_id)
            .outerjoin(
                ChurchDB,
                (ChurchDB.id == ServiceAssignmentDB.scope_id) & (ServiceAssignmentDB.scope_type == "church"),
            )
            .where(
                ServiceAssignmentDB.person_id.in_(person_ids),
                ServiceAssignmentDB.ended_at.is_(None),
            )
        )
        for (
            person_id,
            custom_name,
            service_type_name,
            church_name,
        ) in assignment_rows.all():
            label = service_type_name or custom_name or "?"
            affiliations[person_id].append(("service", label, church_name))

        group_rows = await self.db.execute(
            select(PeopleGroupMembershipDB.person_id, PeopleGroupDB.name)
            .join(PeopleGroupDB, PeopleGroupDB.id == PeopleGroupMembershipDB.group_id)
            .where(
                PeopleGroupMembershipDB.person_id.in_(person_ids),
                PeopleGroupMembershipDB.left_at.is_(None),
            )
        )
        for person_id, group_name in group_rows.all():
            affiliations[person_id].append(("group", group_name, None))

        return affiliations

    async def update_person(
        self,
        person_id: str,
        payload: PersonUpdateRequest,
        *,
        actor_label: str,
        actor_user_id: str,
    ) -> PersonDB | None:
        person = await self.get_person(person_id)
        if not person:
            return None

        before = {
            "firstName": person.first_name,
            "lastName": person.last_name,
            "email": person.email,
            "phone": person.phone,
        }

        if payload.firstName is not None:
            person.first_name = payload.firstName
        if payload.lastName is not None:
            person.last_name = payload.lastName
        if payload.email is not None:
            person.email = payload.email
        if payload.phone is not None:
            person.phone = payload.phone
        await self.db.commit()
        await self.db.refresh(person)

        after = {
            "firstName": person.first_name,
            "lastName": person.last_name,
            "email": person.email,
            "phone": person.phone,
        }
        changes = {field: (before[field], after[field]) for field in before if before[field] != after[field]}
        if changes:
            batch_id = generate_id()
            for field, (old_value, new_value) in changes.items():
                self.db.add(
                    PersonChangeLogDB(
                        id=generate_id(),
                        person_id=person_id,
                        batch_id=batch_id,
                        field=field,
                        old_value=old_value,
                        new_value=new_value,
                        source="admin_manual",
                        actor_label=actor_label,
                        actor_user_id=actor_user_id,
                    )
                )
            await self.db.commit()

        return person

    async def get_change_log(self, person_id: str, *, skip: int = 0, limit: int = 20) -> list[PersonChangeLogDB]:
        """Return change-log rows for one page of batches (most recently touched batch first).

        Pagination is applied to distinct `batch_id`s, not raw rows, so a multi-field
        batch is never split across pages.
        """
        batch_ids_stmt = select(PersonChangeLogDB.batch_id).where(PersonChangeLogDB.person_id == person_id).group_by(PersonChangeLogDB.batch_id).order_by(func.max(PersonChangeLogDB.created_at).desc()).offset(skip).limit(limit)
        batch_ids = (await self.db.execute(batch_ids_stmt)).scalars().all()
        if not batch_ids:
            return []

        stmt = select(PersonChangeLogDB).where(PersonChangeLogDB.batch_id.in_(batch_ids)).order_by(PersonChangeLogDB.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_change_log_batches(self, person_id: str) -> int:
        stmt = select(func.count(func.distinct(PersonChangeLogDB.batch_id))).where(PersonChangeLogDB.person_id == person_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def merge_persons(self, keep_id: str, merge_id: str) -> PersonDB | None:
        keep_person = await self.get_person(keep_id)
        merge_person = await self.get_person(merge_id)
        if not keep_person or not merge_person:
            return None

        await self.db.execute(update(ServiceAssignmentDB).where(ServiceAssignmentDB.person_id == merge_id).values(person_id=keep_id))

        existing_groups = await self.db.execute(
            select(PeopleGroupMembershipDB.group_id).where(
                PeopleGroupMembershipDB.person_id == keep_id,
                PeopleGroupMembershipDB.left_at.is_(None),
            )
        )
        existing_group_ids = {row[0] for row in existing_groups.all()}

        merge_memberships = await self.db.execute(select(PeopleGroupMembershipDB).where(PeopleGroupMembershipDB.person_id == merge_id))
        for membership in merge_memberships.scalars().all():
            if membership.left_at is None and membership.group_id in existing_group_ids:
                await self.db.delete(membership)
            else:
                membership.person_id = keep_id

        if not keep_person.user_id and merge_person.user_id:
            keep_person.user_id = merge_person.user_id

        # Fill any gaps on the survivor with data from the duplicate instead
        # of silently losing it once the duplicate is deleted.
        if not keep_person.first_name and merge_person.first_name:
            keep_person.first_name = merge_person.first_name
        if not keep_person.last_name and merge_person.last_name:
            keep_person.last_name = merge_person.last_name
        if not keep_person.email and merge_person.email:
            keep_person.email = merge_person.email
        if not keep_person.phone and merge_person.phone:
            keep_person.phone = merge_person.phone

        await self.db.delete(merge_person)
        await self.db.commit()
        await self.db.refresh(keep_person)
        return keep_person


def get_directory_repository(
    db: AsyncSession = Depends(get_db),
) -> DirectoryRepository:
    return DirectoryRepository(db)
