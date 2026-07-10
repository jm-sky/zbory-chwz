"""ACL resolution helpers."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.churches.acl_models import RoleDB, UserRoleAssignmentDB
from app.modules.churches.acl_seed import PASTORAL_ROLE_NAMES
from app.modules.churches.db_models import ChurchDB


class AclService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def has_pastoral_access(self, user_id: str, church_id: str) -> bool:
        church = await self._get_church(church_id)
        if not church:
            return False

        scope_filters = [
            (UserRoleAssignmentDB.scope_type == "church")
            & (UserRoleAssignmentDB.scope_id == church_id),
            (UserRoleAssignmentDB.scope_type == "community")
            & (UserRoleAssignmentDB.scope_id == church.community_id),
        ]
        if church.region_id:
            scope_filters.append(
                (UserRoleAssignmentDB.scope_type == "region")
                & (UserRoleAssignmentDB.scope_id == church.region_id)
            )

        result = await self.db.execute(
            select(UserRoleAssignmentDB.id)
            .join(RoleDB, RoleDB.id == UserRoleAssignmentDB.role_id)
            .where(
                UserRoleAssignmentDB.user_id == user_id,
                RoleDB.name.in_(PASTORAL_ROLE_NAMES),
                or_(*scope_filters),
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _get_church(self, church_id: str) -> ChurchDB | None:
        result = await self.db.execute(select(ChurchDB).where(ChurchDB.id == church_id))
        return result.scalar_one_or_none()
