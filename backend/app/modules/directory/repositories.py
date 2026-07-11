"""Repository layer for the people directory (email export) module.

See docs/plans/2026-07-09--mailing-lists.md.
"""

from fastapi import Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.modules.groups.db_models import PeopleGroupMembershipDB


class DirectoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_allowed_church_ids(self, user: User) -> set[str] | None:
        """Church ids the user may export contacts from.

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
        stmt = select(PersonDB).where(PersonDB.email.isnot(None), PersonDB.email != "")

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

        stmt = stmt.order_by(PersonDB.first_name, PersonDB.last_name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


def get_directory_repository(
    db: AsyncSession = Depends(get_db),
) -> DirectoryRepository:
    return DirectoryRepository(db)
