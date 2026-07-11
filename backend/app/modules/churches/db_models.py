"""Database models for church hierarchy."""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.churches.visibility import (
    DEFAULT_CARD_VISIBILITY,
    DEFAULT_EMAIL_VISIBILITY,
    DEFAULT_PHONE_VISIBILITY,
)


class CommunityDB(Base):
    __tablename__ = "communities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    visibility: Mapped[str] = mapped_column(
        String(32), default="hidden", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class RegionDB(Base):
    __tablename__ = "regions"
    __table_args__ = (
        UniqueConstraint("community_id", "slug", name="uq_regions_community_slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    community_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class ChurchDB(Base):
    __tablename__ = "churches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    community_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False
    )
    region_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("regions.id", ondelete="SET NULL"), nullable=True
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(32), default="hidden", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class BranchDB(Base):
    __tablename__ = "branches"
    __table_args__ = (
        UniqueConstraint("church_id", "slug", name="uq_branches_church_slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    church_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(32), default="hidden", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class PersonDB(Base):
    __tablename__ = "persons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        onupdate=lambda: datetime.now(UTC),
    )

    assignments: Mapped[list["ServiceAssignmentDB"]] = relationship(
        back_populates="person"
    )


class ServiceTypeDB(Base):
    __tablename__ = "service_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    suggested_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_senior_tier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    probation_supported: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class ServiceAssignmentDB(Base):
    __tablename__ = "service_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False
    )
    service_type_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("service_types.id", ondelete="SET NULL"), nullable=True
    )
    custom_service_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(36), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    probation_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    card_visibility: Mapped[str] = mapped_column(
        String(32), default=DEFAULT_CARD_VISIBILITY, nullable=False
    )
    phone_visibility: Mapped[str] = mapped_column(
        String(32), default=DEFAULT_PHONE_VISIBILITY, nullable=False
    )
    email_visibility: Mapped[str] = mapped_column(
        String(32), default=DEFAULT_EMAIL_VISIBILITY, nullable=False
    )
    source_contact_person_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    person: Mapped["PersonDB"] = relationship(back_populates="assignments")
    service_type: Mapped["ServiceTypeDB | None"] = relationship()


class ChurchSlugAliasDB(Base):
    __tablename__ = "church_slug_aliases"
    __table_args__ = (
        UniqueConstraint(
            "country_slug", "city_slug", "slug", name="uq_church_slug_path"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    church_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    alias_type: Mapped[str] = mapped_column(String(32), nullable=False)
    country_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    city_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    is_canonical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class CityAliasDB(Base):
    __tablename__ = "city_aliases"
    __table_args__ = (
        UniqueConstraint("country_slug", "alias_slug", name="uq_city_aliases"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    country_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    alias_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    city_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
