"""Database repository implementation for admin operations.

This module provides async repository for admin-level data access
to users across the platform.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.db_models import UserDB

logger = logging.getLogger(__name__)


class AdminRepository:
    """Repository for admin-level data access.

    Provides async database operations for admin users to access
    all users across the platform.
    """

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db

    # User operations
    async def get_all_users(self, skip: int = 0, limit: int = 100) -> list[tuple[UserDB, UserDB | None]]:
        """Get all users with their auth data.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of tuples (UserDB, UserDB) - both refer to same user for consistency
        """
        stmt = select(UserDB).where(UserDB.deleted_at.is_(None)).offset(skip).limit(limit).order_by(UserDB.created_at.desc())
        result = await self.db.execute(stmt)
        users = result.scalars().all()

        # Return tuple format for consistency with service expectations
        users_with_auth: list[tuple[UserDB, UserDB | None]] = [(user, user) for user in users]

        return users_with_auth

    async def get_user_by_id(self, user_id: str) -> tuple[UserDB | None, UserDB | None]:
        """Get user by ID with auth data.

        Args:
            user_id: User ID

        Returns:
            Tuple of (UserDB, UserDB) or (None, None) if not found
        """
        # Get user
        stmt = select(UserDB).where(UserDB.id == user_id, UserDB.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return (None, None)

        return (user, user)
