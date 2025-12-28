"""FastAPI router for user management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.repositories import UserRepository as AuthUserRepository
from app.modules.auth.repositories import (
    get_user_repository as get_auth_user_repository,
)
from app.modules.settings.db_models import UserSettingsDB

from .dependencies import AdminUser, CurrentUser
from .exceptions import UserAlreadyExistsError
from .repositories import UserRepository, get_user_repository
from .schemas import (
    MessageResponse,
    PublicUserResponse,
    UserCreate,
    UserListResponse,
    UserProfileUpdate,
    UserResponse,
    UserUpdate,
)

# Create router
router = APIRouter()


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
    description="Create a new user (admin only)",
)
async def create_user(
    user_data: UserCreate,
    _: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserResponse:
    """Create a new user."""
    try:
        user = await repo.create_user(
            email=user_data.email, name=user_data.name, role=user_data.role
        )
        return UserResponse(**user.to_response())
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.get(
    "/",
    response_model=UserListResponse,
    summary="List users",
    description="Get list of all users with pagination and search",
)
async def list_users(
    _: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=1000, description="Max records to return"),
    include_inactive: bool = Query(default=False, description="Include inactive users"),
    search: str | None = Query(
        default=None, description="Search in name, email, and role"
    ),
) -> UserListResponse:
    """Get list of users with optional search.

    Search is performed across name, email, and role fields.
    Example: ?search=john will find users with 'john' in name, email, or role.
    """
    users = await repo.get_all_users(
        skip=skip, limit=limit, include_inactive=include_inactive, search=search
    )
    total = await repo.count_users(include_inactive=include_inactive, search=search)

    user_responses = [UserResponse(**u.to_response()) for u in users]
    return UserListResponse.create(
        items=user_responses,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get currently authenticated user information",
)
async def get_current_user_info(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get current user information."""
    # Get user response data
    user_data = current_user.to_response()

    return UserResponse(**user_data)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
    description="Update profile information for the authenticated user",
)
async def update_current_user_profile(
    user_data: UserProfileUpdate,
    current_user: CurrentUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserResponse:
    """Update current user's profile details.

    Note: Email updates are not allowed for security reasons.
    """
    updated_user = await repo.update_user(
        user_id=current_user.id,
        name=user_data.name,
        avatar_url=user_data.avatarUrl,
    )
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserResponse(**updated_user.to_response())


@router.get(
    "/{user_id}/public",
    response_model=PublicUserResponse,
    summary="Get public user profile",
    description="Get public profile information for a user (only if profile is public)",
)
async def get_public_user_profile(
    user_id: str,
    auth_repo: Annotated[AuthUserRepository, Depends(get_auth_user_repository)],
    db: AsyncSession = Depends(get_db),
) -> PublicUserResponse:
    """Get public user profile.

    Returns public profile information if:
    - User exists
    - User's profile is set to public (is_public_profile = True)

    Email is only included if:
    - Profile is public AND
    - User's emailPublic setting is True
    """
    # Get user directly from auth repository to access all role fields
    auth_user = await auth_repo.get_user_by_id(user_id)
    if not auth_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found"
        )

    # Check if profile is public
    result = await db.execute(
        select(UserSettingsDB).where(UserSettingsDB.user_id == user_id)
    )
    settings = result.scalars().first()

    # If no settings exist, profile is not public (default is False)
    if not settings or not settings.is_public_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user profile is not public",
        )

    # Build public response - AuthUser has all role fields (isAdmin, isOwner, isPremium)
    return PublicUserResponse(
        id=auth_user.id,
        name=auth_user.name,
        avatarUrl=auth_user.avatarUrl,
        isAdmin=auth_user.isAdmin,
        isOwner=auth_user.isOwner,
        isPremium=auth_user.isPremium,
        email=auth_user.email if settings.is_public_email else None,
        emailPublic=settings.is_public_email,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Get a specific user by their ID",
)
async def get_user(
    user_id: str,
    _: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserResponse:
    """Get user by ID."""
    user = await repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found"
        )
    return UserResponse(**user.to_response())


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update user information (admin only)",
)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    _: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserResponse:
    """Update user information."""
    try:
        user = await repo.update_user(
            user_id=user_id,
            email=user_data.email,
            name=user_data.name,
            role=user_data.role,
            is_active=user_data.isActive,
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
        return UserResponse(**user.to_response())
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Delete user",
    description="Soft delete user (set isActive to false)",
)
async def delete_user(
    user_id: str,
    _: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> MessageResponse:
    """Soft delete user."""
    success = await repo.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found"
        )
    return MessageResponse(message=f"User {user_id} deactivated successfully")


@router.delete(
    "/{user_id}/hard",
    response_model=MessageResponse,
    summary="Permanently delete user",
    description="Permanently delete user from the system (admin only)",
)
async def hard_delete_user(
    user_id: str,
    _: AdminUser,
    repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> MessageResponse:
    """Permanently delete user."""
    success = await repo.hard_delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found"
        )
    return MessageResponse(message=f"User {user_id} permanently deleted")
