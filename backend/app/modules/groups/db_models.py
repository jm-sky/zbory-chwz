"""Database models for people groups (organizational groups independent of a single church).

See docs/plans/2026-07-09--people-groups.md.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.churches.db_models import PersonDB

DEFAULT_GROUP_VISIBILITY = "authenticated"
DEFAULT_GROUP_SCOPE_TYPE = "global"


class PeopleGroupDB(Base):
    __tablename__ = "people_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope_type: Mapped[str] = mapped_column(String(32), default=DEFAULT_GROUP_SCOPE_TYPE, nullable=False)
    scope_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), default=DEFAULT_GROUP_VISIBILITY, nullable=False)
    steward_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        onupdate=lambda: datetime.now(UTC),
    )

    memberships: Mapped[list["PeopleGroupMembershipDB"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class PeopleGroupMembershipDB(Base):
    __tablename__ = "people_group_memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("people_groups.id", ondelete="CASCADE"), nullable=False)
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("persons.id", ondelete="CASCADE"), nullable=False)
    role_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    group: Mapped["PeopleGroupDB"] = relationship(back_populates="memberships")
    person: Mapped["PersonDB"] = relationship()
