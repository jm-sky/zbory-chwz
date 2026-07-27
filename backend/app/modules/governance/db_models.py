"""Database models for the governance module: ACL audit log (G8)."""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.common.crypto.encrypted_types import EncryptedString
from app.core.database import Base


class AclAuditAction(StrEnum):
    ROLE_GRANT = "role.grant"
    ROLE_REVOKE = "role.revoke"
    PERMISSION_SET = "permission.set"
    PERMISSION_CLEAR = "permission.clear"
    INVITE_SENT = "invite.sent"
    INVITE_ACCEPTED = "invite.accepted"
    ASSIGNMENT_CREATE = "assignment.create"
    ASSIGNMENT_DELETE = "assignment.delete"


class AclAuditLogDB(Base):
    """Append-only log of ACL-affecting actions (roles, permission exceptions, invites,
    service-assignment ACL side effects) — who did what, to whom, in which scope.

    Names/emails identify real people, so actor_label/target_label are encrypted at rest
    like the source `persons` columns (migration 072) — the log must not be a backdoor
    around that. There is deliberately no update/delete path; corrections are new rows.
    """

    __tablename__ = "acl_audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Groups the rows written by a single action (e.g. deleting a service assignment can
    # cascade several role/permission revocations) into one entry for the audit UI (G11).
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_label: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    target_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_label: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scope_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    role_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    permission: Mapped[str | None] = mapped_column(String(64), nullable=True)
    effect: Mapped[str | None] = mapped_column(String(8), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Free string, e.g. "ui" | "migration" | "seed" — parity with person_change_log.source.
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="ui")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
