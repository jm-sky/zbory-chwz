"""Pydantic schemas for congregation share links."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ShareableVisibilityLevel = Literal["public", "authenticated", "pastors"]
ShareLinkExpiryDays = Literal[3, 7, 14, 30]


class ShareLinkCreateRequest(BaseModel):
    visibility_level: ShareableVisibilityLevel
    expires_in_days: ShareLinkExpiryDays
    label: str | None = Field(default=None, max_length=255)


class ShareLinkResponse(BaseModel):
    id: str
    token: str
    visibility_level: ShareableVisibilityLevel
    label: str | None = None
    expires_at: datetime
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class ShareLinkListResponse(BaseModel):
    links: list[ShareLinkResponse]
