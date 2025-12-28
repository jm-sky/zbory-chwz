"""Pydantic schemas for user management endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.common.pagination import PaginatedResponse
from .validators import validate_avatar_url


class UserCreate(BaseModel):
    """User creation request schema with camelCase."""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="user", pattern="^(user|admin|moderator)$")


class UserUpdate(BaseModel):
    """User update request schema with camelCase."""

    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = Field(None, pattern="^(user|admin|moderator|owner|premium)$")
    isActive: Optional[bool] = None
    isAdmin: Optional[bool] = None
    isOwner: Optional[bool] = None
    isPremium: Optional[bool] = None


class UserProfileUpdate(BaseModel):
    """Current user profile update schema.

    Note: Email cannot be updated through this endpoint for security reasons.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    avatarUrl: Optional[str] = Field(None, description="Avatar URL (only allowed providers like Gravatar)")

    @field_validator("avatarUrl")
    @classmethod
    def validate_avatar_url(cls, v: str | None) -> str | None:
        """Validate avatar URL against allowed providers."""
        if v is not None and not validate_avatar_url(v):
            raise ValueError("Avatar URL must be from an allowed provider (e.g., Gravatar)")
        return v


class UserResponse(BaseModel):
    """User response schema with camelCase."""

    id: str
    email: EmailStr
    name: str
    role: str
    isActive: bool
    avatarUrl: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class UserListResponse(PaginatedResponse[UserResponse]):
    """User list response with pagination metadata.

    Uses generic PaginatedResponse with consistent pagination fields:
    - data: list of users
    - total: total count
    - page: current page (0-based)
    - limit: items per page
    - hasMore: whether more pages exist
    """

    pass


class PublicUserResponse(BaseModel):
    """Public user profile response schema with camelCase.

    Only includes public information:
    - id, name, avatarUrl, isAdmin, isOwner, isPremium (always public)
    - email (only if user has emailPublic setting enabled)
    """

    id: str
    name: str
    avatarUrl: Optional[str] = None
    isAdmin: bool = False
    isOwner: bool = False
    isPremium: bool = False
    email: Optional[EmailStr] = None  # Only included if emailPublic is True
    emailPublic: bool = False  # Indicates if email is included

    model_config = {"from_attributes": True, "populate_by_name": True}


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
