"""Repository for congregation share link persistence."""

from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.core.database import get_db
from app.modules.sharing.db_models import ShareLinkDB
from app.modules.sharing.schemas import ShareableVisibilityLevel


class ShareLinkRepository:
    """Data access layer for congregation share links."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        *,
        token: str,
        tenant_id: str | None,
        created_by_user_id: str,
        visibility_level: ShareableVisibilityLevel,
        expires_at: datetime,
        label: str | None,
    ) -> ShareLinkDB:
        share_link = ShareLinkDB(
            id=generate_id(),
            token=token,
            tenant_id=tenant_id,
            created_by_user_id=created_by_user_id,
            visibility_level=visibility_level,
            label=label,
            expires_at=expires_at,
        )
        self.db.add(share_link)
        await self.db.commit()
        await self.db.refresh(share_link)
        return share_link

    async def list_active_for_tenant(self, tenant_id: str) -> Sequence[ShareLinkDB]:
        stmt = select(ShareLinkDB).where(ShareLinkDB.tenant_id == tenant_id, ShareLinkDB.revoked_at.is_(None)).order_by(ShareLinkDB.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, link_id: str, tenant_id: str) -> ShareLinkDB | None:
        stmt = select(ShareLinkDB).where(ShareLinkDB.id == link_id, ShareLinkDB.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_for_user(self, user_id: str) -> Sequence[ShareLinkDB]:
        """List a user's own all-congregations (tenant-less) share links."""
        stmt = (
            select(ShareLinkDB)
            .where(
                ShareLinkDB.tenant_id.is_(None),
                ShareLinkDB.created_by_user_id == user_id,
                ShareLinkDB.revoked_at.is_(None),
            )
            .order_by(ShareLinkDB.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_id_for_user(self, link_id: str, user_id: str) -> ShareLinkDB | None:
        stmt = select(ShareLinkDB).where(
            ShareLinkDB.id == link_id,
            ShareLinkDB.tenant_id.is_(None),
            ShareLinkDB.created_by_user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> ShareLinkDB | None:
        stmt = select(ShareLinkDB).where(ShareLinkDB.token == token)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, share_link: ShareLinkDB) -> None:
        share_link.revoked_at = datetime.now(UTC)
        await self.db.commit()

    async def touch_last_used(self, share_link: ShareLinkDB) -> None:
        share_link.last_used_at = datetime.now(UTC)
        await self.db.commit()


def get_share_link_repository(
    db: AsyncSession = Depends(get_db),
) -> ShareLinkRepository:
    """FastAPI dependency to obtain a share link repository."""
    return ShareLinkRepository(db)
