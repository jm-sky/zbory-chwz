"""Append-only ACL audit log writer (G8). Called from every ACL-affecting write path:
role grant/revoke (G5), invite send/accept (G2), permission exceptions (G9), and the
cascading revocation when a service assignment is deleted (G0.1/§5.3)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.modules.auth.models import User
from app.modules.governance.db_models import AclAuditAction, AclAuditLogDB


class AclAuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        *,
        actor: User | None,
        action: AclAuditAction,
        target_user_id: str | None,
        target_label: str,
        scope_type: str | None = None,
        scope_id: str | None = None,
        role_name: str | None = None,
        permission: str | None = None,
        effect: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        source: str = "ui",
        batch_id: str | None = None,
    ) -> str:
        """Write one audit row. Does not commit — participates in the caller's own
        transaction (matching every other write path in this codebase).

        Returns the batch_id used, so callers writing several rows for one action (e.g.
        cascading role revocations on assignment delete) can group them explicitly by
        passing the same batch_id back in on subsequent calls.
        """
        resolved_batch_id = batch_id or generate_id()
        entry = AclAuditLogDB(
            id=generate_id(),
            batch_id=resolved_batch_id,
            actor_user_id=actor.id if actor else None,
            actor_label=actor.name if actor else "system",
            target_user_id=target_user_id,
            target_label=target_label,
            action=action.value,
            scope_type=scope_type,
            scope_id=scope_id,
            role_name=role_name,
            permission=permission,
            effect=effect,
            old_value=old_value,
            new_value=new_value,
            source=source,
            created_at=datetime.now(UTC),
        )
        self.db.add(entry)
        await self.db.flush()
        return resolved_batch_id
