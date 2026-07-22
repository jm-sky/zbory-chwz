"""Business logic for congregation share links."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import Depends

from app.modules.sharing.db_models import ShareLinkDB
from app.modules.sharing.repositories import (
    ShareLinkRepository,
    get_share_link_repository,
)
from app.modules.sharing.schemas import (
    ShareLinkCreateVisibilityLevel,
    ShareLinkExpiryDays,
)

ResolveFailureReason = Literal["not_found", "expired", "revoked"]


class ShareLinkService:
    """Creates and resolves anonymous, time-limited congregation share links."""

    def __init__(self, repository: ShareLinkRepository):
        self.repository = repository

    async def create_share_link(
        self,
        *,
        tenant_id: str | None,
        created_by_user_id: str,
        visibility_level: ShareLinkCreateVisibilityLevel,
        expires_in_days: ShareLinkExpiryDays,
        label: str | None,
    ) -> ShareLinkDB:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)
        return await self.repository.create(
            token=token,
            tenant_id=tenant_id,
            created_by_user_id=created_by_user_id,
            visibility_level=visibility_level,
            expires_at=expires_at,
            label=label,
        )

    async def resolve_token(self, token: str) -> tuple[ShareLinkDB | None, ResolveFailureReason | None]:
        share_link = await self.repository.get_by_token(token)
        if share_link is None:
            return None, "not_found"
        if share_link.revoked_at is not None:
            return None, "revoked"

        expires_at = share_link.expires_at
        if expires_at.tzinfo is None:
            # SQLite drops tzinfo on round-trip; the column is always stored as UTC.
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            return None, "expired"

        await self.repository.touch_last_used(share_link)
        return share_link, None


def get_share_link_service(
    repository: ShareLinkRepository = Depends(get_share_link_repository),
) -> ShareLinkService:
    """FastAPI dependency to obtain a share link service."""
    return ShareLinkService(repository)
