"""Repository for governance role assignments (G5) — manual ACL role grants, distinct
from the ones created as a side effect of a service assignment (churches module)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.id_utils import generate_id
from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.churches.acl_grant_rules import assert_can_grant_role, assert_can_revoke_role
from app.modules.churches.acl_models import RoleDB, UserPermissionDB, UserRoleAssignmentDB
from app.modules.churches.acl_seed import Permission, ensure_acl_roles
from app.modules.churches.permission_service import PermissionService
from app.modules.governance.audit_service import AclAuditService
from app.modules.governance.db_models import AclAuditAction, AclAuditLogDB

if TYPE_CHECKING:
    from app.modules.churches.permission_cache import PermissionCache


async def _community_id_for_scope(permission_service: PermissionService, scope_type: str, scope_id: str) -> str:
    chain = await permission_service.scope_chain(scope_type, scope_id)
    community_id = next((sid for st, sid in chain if st == "community"), None)
    if not community_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope not found")
    return community_id


class GovernanceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AclAuditService(db)

    async def list_role_assignments(self, scope_type: str, scope_id: str) -> list[UserRoleAssignmentDB]:
        result = await self.db.execute(
            select(UserRoleAssignmentDB)
            .where(
                UserRoleAssignmentDB.scope_type == scope_type,
                UserRoleAssignmentDB.scope_id == scope_id,
            )
            .options(selectinload(UserRoleAssignmentDB.role))
            .order_by(UserRoleAssignmentDB.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_role_assignment(
        self,
        *,
        actor: User,
        permission_service: PermissionService,
        target_user_id: str,
        role_name: str,
        scope_type: str,
        scope_id: str,
        cache: "PermissionCache | None" = None,
    ) -> UserRoleAssignmentDB:
        community_id = await _community_id_for_scope(permission_service, scope_type, scope_id)
        await assert_can_grant_role(
            permission_service,
            actor,
            role_name,
            (scope_type, scope_id),
            community_id=community_id,
        )

        roles_by_name = await ensure_acl_roles(self.db)
        role = roles_by_name.get(role_name)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        existing = await self.db.execute(
            select(UserRoleAssignmentDB).where(
                UserRoleAssignmentDB.user_id == target_user_id,
                UserRoleAssignmentDB.role_id == role.id,
                UserRoleAssignmentDB.scope_type == scope_type,
                UserRoleAssignmentDB.scope_id == scope_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already granted in this scope")

        assignment = UserRoleAssignmentDB(
            id=generate_id(),
            user_id=target_user_id,
            role_id=role.id,
            scope_type=scope_type,
            scope_id=scope_id,
            source_assignment_id=None,
        )
        self.db.add(assignment)

        target_label = await self._user_label(target_user_id)
        await self.audit.record(
            actor=actor,
            action=AclAuditAction.ROLE_GRANT,
            target_user_id=target_user_id,
            target_label=target_label,
            scope_type=scope_type,
            scope_id=scope_id,
            role_name=role_name,
        )

        await self.db.commit()
        if cache:
            await cache.invalidate_user(target_user_id)

        await self.db.refresh(assignment)
        reloaded = await self.db.execute(select(UserRoleAssignmentDB).where(UserRoleAssignmentDB.id == assignment.id).options(selectinload(UserRoleAssignmentDB.role)))
        return reloaded.scalar_one()

    async def delete_role_assignment(
        self,
        *,
        actor: User,
        permission_service: PermissionService,
        assignment_id: str,
        cache: "PermissionCache | None" = None,
    ) -> None:
        result = await self.db.execute(select(UserRoleAssignmentDB).where(UserRoleAssignmentDB.id == assignment_id).options(selectinload(UserRoleAssignmentDB.role)))
        assignment = result.scalar_one_or_none()
        if not assignment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role assignment not found")

        if assignment.source_assignment_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This grant comes from a service assignment — delete the assignment instead",
            )

        role_name = assignment.role.name
        scope_type = assignment.scope_type
        scope_id = assignment.scope_id
        community_id = await _community_id_for_scope(permission_service, scope_type, scope_id)

        await assert_can_revoke_role(
            permission_service,
            actor,
            role_name,
            (scope_type, scope_id),
            community_id=community_id,
        )

        if role_name == "bishop" and scope_type == "community":
            remaining = await self.db.execute(
                select(UserRoleAssignmentDB.id)
                .join(RoleDB, RoleDB.id == UserRoleAssignmentDB.role_id)
                .where(
                    RoleDB.name == "bishop",
                    UserRoleAssignmentDB.scope_type == "community",
                    UserRoleAssignmentDB.scope_id == scope_id,
                    UserRoleAssignmentDB.id != assignment_id,
                )
            )
            if not remaining.first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot remove the last bishop grant for this community",
                )

        target_user_id = assignment.user_id
        target_label = await self._user_label(target_user_id)
        await self.db.delete(assignment)
        await self.audit.record(
            actor=actor,
            action=AclAuditAction.ROLE_REVOKE,
            target_user_id=target_user_id,
            target_label=target_label,
            scope_type=scope_type,
            scope_id=scope_id,
            role_name=role_name,
        )
        await self.db.commit()

        if cache:
            await cache.invalidate_user(target_user_id)

    async def _user_label(self, user_id: str) -> str:
        from app.modules.auth.db_models import UserDB

        result = await self.db.execute(select(UserDB.name).where(UserDB.id == user_id))
        name = result.scalar_one_or_none()
        return name or user_id

    async def _assert_can_set_exception(
        self,
        *,
        actor: User,
        permission_service: PermissionService,
        permission: str,
        scope_type: str,
        scope_id: str,
    ) -> None:
        """Subset rule (§5.1) extended from roles to individual permissions (G9): the caller
        must hold `services.manage` in this scope *and* already hold the permission they're
        setting an exception for — for both allow and deny, otherwise a low-privileged actor
        could deny a permission held by someone above them."""
        if actor.isAdmin or actor.isOwner:
            return

        scope: tuple[str, str] = (scope_type, scope_id)
        if not await permission_service.resolve(actor, Permission.SERVICES_MANAGE, scope):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if not await permission_service.resolve(actor, permission, scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot set an exception for a permission you do not hold in this scope",
            )

    async def list_user_permissions(self, user_id: str, scope_type: str, scope_id: str) -> list[UserPermissionDB]:
        result = await self.db.execute(
            select(UserPermissionDB)
            .where(
                UserPermissionDB.user_id == user_id,
                UserPermissionDB.scope_type == scope_type,
                UserPermissionDB.scope_id == scope_id,
            )
            .order_by(UserPermissionDB.permission)
        )
        return list(result.scalars().all())

    async def upsert_user_permission(
        self,
        *,
        actor: User,
        permission_service: PermissionService,
        target_user_id: str,
        scope_type: str,
        scope_id: str,
        permission: str,
        effect: str,
        cache: "PermissionCache | None" = None,
    ) -> UserPermissionDB:
        await self._assert_can_set_exception(
            actor=actor,
            permission_service=permission_service,
            permission=permission,
            scope_type=scope_type,
            scope_id=scope_id,
        )

        existing = await self.db.execute(
            select(UserPermissionDB).where(
                UserPermissionDB.user_id == target_user_id,
                UserPermissionDB.scope_type == scope_type,
                UserPermissionDB.scope_id == scope_id,
                UserPermissionDB.permission == permission,
            )
        )
        row = existing.scalar_one_or_none()

        if row and row.source_assignment_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This exception comes from a service assignment — delete the assignment instead",
            )

        old_effect = row.effect if row else None
        if row:
            row.effect = effect
            row.created_by = actor.id
        else:
            row = UserPermissionDB(
                id=generate_id(),
                user_id=target_user_id,
                scope_type=scope_type,
                scope_id=scope_id,
                permission=permission,
                effect=effect,
                source_assignment_id=None,
                created_by=actor.id,
            )
            self.db.add(row)

        target_label = await self._user_label(target_user_id)
        await self.audit.record(
            actor=actor,
            action=AclAuditAction.PERMISSION_SET,
            target_user_id=target_user_id,
            target_label=target_label,
            scope_type=scope_type,
            scope_id=scope_id,
            permission=permission,
            effect=effect,
            old_value=old_effect,
            new_value=effect,
        )

        await self.db.commit()
        if cache:
            await cache.invalidate_user(target_user_id)

        await self.db.refresh(row)
        return row

    async def delete_user_permission(
        self,
        *,
        actor: User,
        permission_service: PermissionService,
        exception_id: str,
        cache: "PermissionCache | None" = None,
    ) -> None:
        result = await self.db.execute(select(UserPermissionDB).where(UserPermissionDB.id == exception_id))
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exception not found")

        if row.source_assignment_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This exception comes from a service assignment — delete the assignment instead",
            )

        await self._assert_can_set_exception(
            actor=actor,
            permission_service=permission_service,
            permission=row.permission,
            scope_type=row.scope_type,
            scope_id=row.scope_id,
        )

        target_user_id = row.user_id
        target_label = await self._user_label(target_user_id)
        old_effect = row.effect
        await self.db.delete(row)
        await self.audit.record(
            actor=actor,
            action=AclAuditAction.PERMISSION_CLEAR,
            target_user_id=target_user_id,
            target_label=target_label,
            scope_type=row.scope_type,
            scope_id=row.scope_id,
            permission=row.permission,
            old_value=old_effect,
            new_value=None,
        )
        await self.db.commit()

        if cache:
            await cache.invalidate_user(target_user_id)

    async def list_audit_log(
        self,
        *,
        scope_type: str,
        scope_id: str,
        target_user_id: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[AclAuditLogDB]:
        """Returns every row belonging to the page of *batches* (ordered by each batch's
        latest row, newest first) selected by skip/limit — not a flat row-level page. Mirrors
        DirectoryRepository.get_change_log / count_change_log_batches (directory/repositories.py)."""
        batch_stmt = select(AclAuditLogDB.batch_id, func.max(AclAuditLogDB.created_at).label("latest")).where(
            AclAuditLogDB.scope_type == scope_type,
            AclAuditLogDB.scope_id == scope_id,
        )
        if target_user_id:
            batch_stmt = batch_stmt.where(AclAuditLogDB.target_user_id == target_user_id)
        batch_stmt = batch_stmt.group_by(AclAuditLogDB.batch_id).order_by(func.max(AclAuditLogDB.created_at).desc()).offset(skip).limit(limit)

        batch_result = await self.db.execute(batch_stmt)
        batch_ids = [row.batch_id for row in batch_result.all()]
        if not batch_ids:
            return []

        rows_result = await self.db.execute(select(AclAuditLogDB).where(AclAuditLogDB.batch_id.in_(batch_ids)).order_by(AclAuditLogDB.created_at.desc()))
        return list(rows_result.scalars().all())

    async def count_audit_log_batches(
        self,
        *,
        scope_type: str,
        scope_id: str,
        target_user_id: str | None = None,
    ) -> int:
        stmt = select(func.count(func.distinct(AclAuditLogDB.batch_id))).where(
            AclAuditLogDB.scope_type == scope_type,
            AclAuditLogDB.scope_id == scope_id,
        )
        if target_user_id:
            stmt = stmt.where(AclAuditLogDB.target_user_id == target_user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()


def get_governance_repository(db: AsyncSession = Depends(get_db)) -> GovernanceRepository:
    return GovernanceRepository(db)
