"""ACL resolution helpers — thin wrapper over PermissionService."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.churches.acl_seed import Permission
from app.modules.churches.permission_cache import PermissionCache
from app.modules.churches.permission_service import PermissionService, get_permission_cache


class AclService:
    def __init__(self, permission_service: PermissionService) -> None:
        self._permissions = permission_service

    async def has_permission(self, user: User, permission: str) -> bool:
        return await self._permissions.has_anywhere(user, permission)

    async def has_pastoral_access(self, user: User, church_id: str) -> bool:
        return await self._permissions.resolve(user, Permission.CHURCH_VIEW_PASTORAL, ("church", church_id))


def get_acl_service(
    db: AsyncSession = Depends(get_db),
    cache: PermissionCache = Depends(get_permission_cache),
) -> AclService:
    return AclService(PermissionService(db, cache))
