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
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.crypto.encrypted_types import (
    EncryptedString,
    hmac_email,
    hmac_phone_digits,
)
from app.core.database import Base
from app.modules.churches.visibility import (
    DEFAULT_EMAIL_VISIBILITY,
    DEFAULT_PHONE_VISIBILITY,
    DEFAULT_PROFILE_VISIBILITY,
)


class CommunityDB(Base):
    __tablename__ = "communities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    visibility: Mapped[str] = mapped_column(String(32), default="hidden", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class RegionDB(Base):
    __tablename__ = "regions"
    __table_args__ = (UniqueConstraint("community_id", "slug", name="uq_regions_community_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    community_id: Mapped[str] = mapped_column(String(36), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ChurchDB(Base):
    __tablename__ = "churches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    community_id: Mapped[str] = mapped_column(String(36), ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    region_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("regions.id", ondelete="SET NULL"), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), default="hidden", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class BranchDB(Base):
    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("church_id", "slug", name="uq_branches_church_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    church_id: Mapped[str] = mapped_column(String(36), ForeignKey("churches.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), default="hidden", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class PersonDB(Base):
    __tablename__ = "persons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    first_name: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    last_name: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    email: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    # HMAC-SHA256 blind index of the normalized e-mail, for exact-match lookup
    # (e.g. sender_resolver._find_person) without decrypting every row — see
    # app/common/crypto/encrypted_types.hmac_email.
    email_bidx: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    # Same purpose as email_bidx, digits-only normalized — used by
    # find_person_by_email_or_phone's exact-match phone lookup (Google
    # Contacts import matching).
    phone_bidx: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        onupdate=lambda: datetime.now(UTC),
    )

    assignments: Mapped[list["ServiceAssignmentDB"]] = relationship(back_populates="person")


@event.listens_for(PersonDB.email, "set")
def _sync_person_email_bidx(target: PersonDB, value: str | None, oldvalue: object, initiator: object) -> None:
    """Keep email_bidx in lockstep with email on every assignment.

    Fires on constructor kwargs and plain `person.email = ...` writes (there
    are many call sites across churches/directory/google_contacts/congregations
    repositories) but not on ORM load from the database, so this can't drift
    out of sync with the encrypted column without also touching every write
    site individually.
    """
    target.email_bidx = hmac_email(value)


@event.listens_for(PersonDB.phone, "set")
def _sync_person_phone_bidx(target: PersonDB, value: str | None, oldvalue: object, initiator: object) -> None:
    target.phone_bidx = hmac_phone_digits(value)


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
    probation_supported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ServiceAssignmentDB(Base):
    __tablename__ = "service_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    service_type_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("service_types.id", ondelete="SET NULL"), nullable=True)
    custom_service_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(36), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    probation_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    show_on_list: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    profile_visibility: Mapped[str] = mapped_column(String(32), default=DEFAULT_PROFILE_VISIBILITY, nullable=False)
    phone_visibility: Mapped[str] = mapped_column(String(32), default=DEFAULT_PHONE_VISIBILITY, nullable=False)
    email_visibility: Mapped[str] = mapped_column(String(32), default=DEFAULT_EMAIL_VISIBILITY, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    person: Mapped["PersonDB"] = relationship(back_populates="assignments")
    service_type: Mapped["ServiceTypeDB | None"] = relationship()


class ChurchSlugAliasDB(Base):
    __tablename__ = "church_slug_aliases"
    __table_args__ = (UniqueConstraint("country_slug", "city_slug", "slug", name="uq_church_slug_path"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    church_id: Mapped[str] = mapped_column(String(36), ForeignKey("churches.id", ondelete="CASCADE"), nullable=False)
    alias_type: Mapped[str] = mapped_column(String(32), nullable=False)
    country_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    city_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    is_canonical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class CityAliasDB(Base):
    __tablename__ = "city_aliases"
    __table_args__ = (UniqueConstraint("country_slug", "alias_slug", name="uq_city_aliases"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    country_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    alias_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    city_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
