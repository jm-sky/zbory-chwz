"""Repository for congregation operations (addresses, service times, contact persons)."""

import logging
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.core.database import get_db
from app.modules.congregations.db_models import (
    CongregationAddressDB,
    CongregationServiceTimeDB,
)
from app.modules.congregations.geo import DEFAULT_COUNTRY

logger = logging.getLogger(__name__)


class CongregationRepository:
    """Data access layer for congregation addresses, service times, and contact persons."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Address operations
    async def get_address_by_tenant_id(self, tenant_id: str) -> CongregationAddressDB | None:
        """Get address for a tenant."""
        stmt = select(CongregationAddressDB).where(CongregationAddressDB.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_update_address(
        self,
        tenant_id: str,
        *,
        street: str | None = None,
        city: str,
        postal_code: str | None = None,
        province: str | None = None,
        country: str = DEFAULT_COUNTRY,
        status: str = "draft",
    ) -> CongregationAddressDB:
        """Create or update address for a tenant."""
        existing = await self.get_address_by_tenant_id(tenant_id)
        if existing:
            existing.street = street
            existing.city = city
            existing.postal_code = postal_code
            existing.province = province
            existing.country = country
            existing.status = status
            existing.updated_at = datetime.now(UTC)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        address = CongregationAddressDB(
            id=generate_id(),
            tenant_id=tenant_id,
            street=street,
            city=city,
            postal_code=postal_code,
            province=province,
            country=country,
            status=status,
        )
        self.db.add(address)
        await self.db.commit()
        await self.db.refresh(address)
        return address

    async def touch_last_updated(self, tenant_id: str, label: str) -> None:
        """Stamp the "last updated by" badge shown on the congregation profile.

        No-op if the tenant has no address row yet - the e-mail import flow
        only ever updates existing congregations, so this should always find
        one in practice; a paste-import that creates a brand-new congregation
        writes street/city/etc. via create_or_update_address first.
        """
        existing = await self.get_address_by_tenant_id(tenant_id)
        if existing is None:
            return
        existing.last_updated_at = datetime.now(UTC)
        existing.last_updated_label = label
        await self.db.commit()

    async def get_addresses_by_status(self, statuses: Sequence[str]) -> dict[str, CongregationAddressDB]:
        """Get addresses with any of the given statuses, keyed by tenant id."""
        stmt = select(CongregationAddressDB).where(CongregationAddressDB.status.in_(statuses))
        result = await self.db.execute(stmt)
        return {address.tenant_id: address for address in result.scalars()}

    async def get_service_times_for_tenants(self, tenant_ids: Sequence[str]) -> dict[str, list[CongregationServiceTimeDB]]:
        """Get service times for many tenants at once, keyed by tenant id."""
        if not tenant_ids:
            return {}
        stmt = select(CongregationServiceTimeDB).where(CongregationServiceTimeDB.tenant_id.in_(tenant_ids)).order_by(CongregationServiceTimeDB.order, CongregationServiceTimeDB.created_at)
        result = await self.db.execute(stmt)
        grouped: dict[str, list[CongregationServiceTimeDB]] = defaultdict(list)
        for service_time in result.scalars():
            grouped[service_time.tenant_id].append(service_time)
        return grouped

    async def delete_address(self, tenant_id: str) -> None:
        """Delete address for a tenant."""
        address = await self.get_address_by_tenant_id(tenant_id)
        if address:
            await self.db.delete(address)
            await self.db.commit()

    # Service times operations
    async def get_service_times_by_tenant_id(self, tenant_id: str) -> list[CongregationServiceTimeDB]:
        """Get all service times for a tenant."""
        stmt = select(CongregationServiceTimeDB).where(CongregationServiceTimeDB.tenant_id == tenant_id).order_by(CongregationServiceTimeDB.order, CongregationServiceTimeDB.created_at)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_service_time(
        self,
        tenant_id: str,
        *,
        day: str,
        time: str,
        order: int = 0,
    ) -> CongregationServiceTimeDB:
        """Create a service time for a tenant."""
        service_time = CongregationServiceTimeDB(
            id=generate_id(),
            tenant_id=tenant_id,
            day=day,
            time=time,
            order=order,
        )
        self.db.add(service_time)
        await self.db.commit()
        await self.db.refresh(service_time)
        return service_time

    async def delete_service_time(self, tenant_id: str, service_time_id: str) -> bool:
        """Delete a service time belonging to the given tenant."""
        stmt = select(CongregationServiceTimeDB).where(
            CongregationServiceTimeDB.id == service_time_id,
            CongregationServiceTimeDB.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        service_time = result.scalar_one_or_none()
        if not service_time:
            return False
        await self.db.delete(service_time)
        await self.db.commit()
        return True

    async def delete_all_service_times(self, tenant_id: str) -> None:
        """Delete all service times for a tenant."""
        stmt = select(CongregationServiceTimeDB).where(CongregationServiceTimeDB.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        service_times = result.scalars().all()
        for st in service_times:
            await self.db.delete(st)
        await self.db.commit()


def get_congregation_repository(
    db: AsyncSession = Depends(get_db),
) -> CongregationRepository:
    """FastAPI dependency to obtain a congregation repository."""
    return CongregationRepository(db)
