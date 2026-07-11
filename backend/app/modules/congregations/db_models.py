"""Database models for congregations (addresses, service times)."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.congregations.geo import DEFAULT_COUNTRY


class CongregationAddressDB(Base):
    """Address for a congregation (tenant)."""

    __tablename__ = "congregation_addresses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    church_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("churches.id", ondelete="CASCADE"), nullable=True)
    street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(255), nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # ISO 3166-1 alpha-2; see app/modules/congregations/geo.py
    country: Mapped[str] = mapped_column(String(2), default=DEFAULT_COUNTRY, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        onupdate=lambda: datetime.now(UTC),
    )


class CongregationServiceTimeDB(Base):
    """Service time for a congregation."""

    __tablename__ = "congregation_service_times"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    church_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("churches.id", ondelete="CASCADE"), nullable=True)
    day: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "niedziela", "środa"
    time: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g., "11:00", "19:00"
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
