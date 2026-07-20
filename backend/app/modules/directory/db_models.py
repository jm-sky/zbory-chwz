"""Database models for the people directory module."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.crypto.encrypted_types import EncryptedString
from app.core.database import Base


class PersonChangeLogDB(Base):
    """Field-level change history for a person's directory record."""

    __tablename__ = "person_change_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    # Groups the rows written by a single action (e.g. one PATCH that changes several fields)
    # so the change-history UI can render one tile per action instead of one per field.
    batch_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # "firstName" | "lastName" | "email" | "phone"
    field: Mapped[str] = mapped_column(String(32), nullable=False)
    # Encrypted at rest, same as the source persons columns (see PersonDB).
    old_value: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    new_value: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    # "admin_manual" for now; kept as a free string for parity with congregation_change_log.
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_label: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
