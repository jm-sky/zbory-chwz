"""Database models for the clergy e-mail import pipeline.

See docs/plans/2026-07-13--clergy-email-updates.md.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EmailImportMessageDB(Base):
    """One inbound e-mail polled from the clergy update mailbox."""

    __tablename__ = "email_import_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # RFC 5322 Message-ID header, used to avoid reprocessing the same e-mail
    # on repeated IMAP polls. Nullable: some malformed mail lacks it.
    message_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_from: Mapped[str] = mapped_column(String(500), nullable=False)
    sender_person_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    resolved_tenant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    # "own_church" | "matched_by_name" | "unauthorized" | "unknown_sender" | "ambiguous"
    resolution: Mapped[str] = mapped_column(String(32), nullable=False)
    # SPF/DKIM/DMARC verdicts parsed from the Authentication-Results header, e.g. "pass"/"fail"/"none".
    auth_spf: Mapped[str | None] = mapped_column(String(16), nullable=True)
    auth_dkim: Mapped[str | None] = mapped_column(String(16), nullable=True)
    auth_dmarc: Mapped[str | None] = mapped_column(String(16), nullable=True)
    extraction_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "pending" | "auto_applied" | "approved" | "rejected"
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class CongregationChangeLogDB(Base):
    """Field-level change history for a congregation, from any update path."""

    __tablename__ = "congregation_change_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    # Groups the rows written by a single action (e.g. one form save that changes several fields)
    # so the change-history UI can render one tile per action instead of one per field.
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # "address" | "contact"
    section: Mapped[str] = mapped_column(String(16), nullable=False)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "admin_manual" | "import_paste" | "email_auto" | "email_reviewed"
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_label: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_person_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    email_import_message_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("email_import_messages.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
