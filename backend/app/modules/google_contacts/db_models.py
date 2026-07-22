"""Database model for Google Contacts (People API) connections.

See docs/plans/2026-07-10--google-contacts-sync.md.

This is deliberately separate from ``oauth_connections`` (login identity
linking, no tokens stored): a Google Contacts connection persists an
access/refresh token pair so the app can call the People API later, on a
user's behalf, independently of how that user logs in.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# Scope granted so far for this connection. Starts at "readonly" (import);
# upgraded to "readonly_write" once the user grants the export/write scope
# via incremental authorization (Phase 4).
GoogleContactsScope = str  # "readonly" | "readonly_write"


class GoogleContactsConnectionDB(Base):
    __tablename__ = "google_contacts_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="readonly")
    access_token: Mapped[str] = mapped_column(Text, nullable=False)  # encrypted
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)  # encrypted
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<GoogleContactsConnectionDB(id={self.id}, user_id={self.user_id}, scope={self.scope})>"


class GoogleContactsImportLogDB(Base):
    """Audit trail for Google Contacts import decisions (Phase 3).

    One row per contact the admin decided on (create/update/skip), regardless
    of whether it resulted in a church or a person record.
    """

    __tablename__ = "google_contacts_import_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    google_resource_name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(16), nullable=False)  # church | person
    matched_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(16), nullable=False)  # created | updated | skipped
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    def __repr__(self) -> str:
        return f"<GoogleContactsImportLogDB(id={self.id}, entity_type={self.entity_type}, action={self.action})>"
