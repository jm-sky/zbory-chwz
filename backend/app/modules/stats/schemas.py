"""Pydantic schemas for stats endpoints."""

from pydantic import BaseModel


class UserStatsResponse(BaseModel):
    """Response schema for user statistics."""

    total: int
    newThisMonth: int
