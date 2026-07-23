"""Database model for congregation share links."""

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ShareLinkDB(Base):
    __tablename__ = "congregation_share_links"
    __table_args__ = (
        CheckConstraint(
            "visibility_level IN ('public', 'authenticated', 'pastors')",
            name="ck_congregation_share_links_visibility_level",
        ),
        Index("ix_congregation_share_links_tenant_active", "tenant_id", "revoked_at"),
        Index(
            "ix_congregation_share_links_creator_active",
            "created_by_user_id",
            "revoked_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # NULL means this link isn't scoped to one congregation: it resolves to every
    # published congregation the creator (an admin/owner) can see.
    tenant_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    visibility_level: Mapped[str] = mapped_column(String(16), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
