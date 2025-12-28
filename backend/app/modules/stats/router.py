"""FastAPI router for statistics endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.db_models import UserDB

from .schemas import UserStatsResponse

# Create router
router = APIRouter()


def get_current_month_start() -> datetime:
    """Get the start of the current month in UTC."""
    now = datetime.now(UTC)
    return datetime(now.year, now.month, 1, tzinfo=UTC)


@router.get(
    "/users",
    response_model=UserStatsResponse,
    summary="Get user statistics",
    description="Get total users and new users this month",
    tags=["Statistics"],
)
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
) -> UserStatsResponse:
    """Get user statistics.

    Returns:
        Total users and count of new users created this month
    """
    month_start = get_current_month_start()

    # Count total users (excluding soft-deleted)
    total_stmt = select(func.count(UserDB.id)).where(UserDB.deleted_at.is_(None))
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 0

    # Count new users this month
    new_this_month_stmt = select(func.count(UserDB.id)).where(UserDB.created_at >= month_start).where(UserDB.deleted_at.is_(None))
    new_this_month_result = await db.execute(new_this_month_stmt)
    new_this_month = new_this_month_result.scalar() or 0

    return UserStatsResponse(total=total, newThisMonth=new_this_month)
