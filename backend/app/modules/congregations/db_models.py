"""Database models for congregations (addresses, service times)."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.crypto.encrypted_types import EncryptedString
from app.core.database import Base
from app.modules.congregations.geo import DEFAULT_COUNTRY


class CongregationAddressDB(Base):
    """Address for a congregation (tenant)."""

    __tablename__ = "congregation_addresses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    church_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("churches.id", ondelete="CASCADE"), nullable=True)
    street: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    city: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    postal_code: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    province: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    # ISO 3166-1 alpha-2; see app/modules/congregations/geo.py
    country: Mapped[str] = mapped_column(String(2), default=DEFAULT_COUNTRY, nullable=False)
    # Public congregation contact info; same status-gated visibility as the
    # rest of the address, no per-field visibility like ServiceAssignmentDB's
    # phone/email. iban stores the full canonical IBAN (always with a country
    # prefix, no spaces); display formatting is country-dependent (see
    # src/shared/utils/formatIban.ts).
    website: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    email: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    iban: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    # GPS coordinates for map display. Stored as encrypted decimal strings (like the
    # rest of the address) since distance filtering happens entirely client-side —
    # the DB never needs to do numeric WHERE/ORDER BY on these columns, so encrypting
    # them costs nothing and keeps drafts protected the same way as street/city.
    latitude: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    longitude: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    # Whether coordinates have been set: pending (none yet) | manual (typed,
    # dragged on the map, or accepted from a geocode preview). Not PII, kept plain.
    geocode_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    # Denormalized from congregation_change_log for a fast "last updated by"
    # badge (see docs/plans/2026-07-13--clergy-email-updates.md) without
    # joining the full history on every profile page load.
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        onupdate=lambda: datetime.now(UTC),
    )


def decode_coordinate(value: str | None) -> float | None:
    """Convert a stored (already-decrypted) coordinate string back to float
    for API responses. The ORM column is str-typed because it's an
    EncryptedString; response schemas expose it as float."""
    return float(value) if value is not None else None


class CongregationServiceTimeDB(Base):
    """Service time for a congregation."""

    __tablename__ = "congregation_service_times"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    church_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("churches.id", ondelete="CASCADE"), nullable=True)
    day: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "niedziela", "środa"
    time: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g., "11:00", "19:00"
    description: Mapped[str | None] = mapped_column(String(256), nullable=True)  # e.g., "Modlitwa nocna"
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
