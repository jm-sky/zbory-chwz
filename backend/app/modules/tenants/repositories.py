"""Repository for tenant operations.

Uses composition (helper functions) for ID generation.
"""

import logging
from datetime import UTC, datetime

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.common.id_utils import generate_id
from app.modules.tenants.db_models import TenantDB, TenantMembershipDB

logger = logging.getLogger(__name__)


class TenantRepository:
    """Data access layer for tenants and memberships."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(
        self, user_id: str
    ) -> list[tuple[TenantDB, TenantMembershipDB]]:
        stmt = (
            select(TenantDB, TenantMembershipDB)
            .join(TenantMembershipDB, TenantMembershipDB.tenant_id == TenantDB.id)
            .where(TenantMembershipDB.user_id == user_id)
            .order_by(TenantDB.created_at)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [(row[0], row[1]) for row in rows]

    async def list_all(self) -> list[TenantDB]:
        stmt = select(TenantDB).order_by(TenantDB.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_tenant(
        self, *, name: str, description: str | None, owner_user_id: str
    ) -> tuple[TenantDB, TenantMembershipDB]:
        tenant_id = generate_id()
        tenant = TenantDB(
            id=tenant_id,
            name=name,
            description=description,
            owner_id=owner_user_id,
        )
        membership = TenantMembershipDB(
            tenant_id=tenant_id,
            user_id=owner_user_id,
            role="owner",
        )

        self.db.add(tenant)
        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant, membership

    async def add_member(
        self, tenant_id: str, user_id: str, role: str = "member"
    ) -> TenantMembershipDB:
        stmt = select(TenantMembershipDB).where(
            TenantMembershipDB.tenant_id == tenant_id,
            TenantMembershipDB.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            logger.info("User %s already member of tenant %s", user_id, tenant_id)
            return existing

        membership = TenantMembershipDB(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def get_tenant(self, tenant_id: str) -> TenantDB | None:
        result = await self.db.execute(select(TenantDB).where(TenantDB.id == tenant_id))
        return result.scalar_one_or_none()


def get_tenant_repository(db: AsyncSession = Depends(get_db)) -> TenantRepository:
    """FastAPI dependency to obtain a tenant repository."""
    return TenantRepository(db)
