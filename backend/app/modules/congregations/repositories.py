"""Repository for congregation operations (addresses, service times, contact persons)."""

import logging
from datetime import UTC, datetime
from typing import List

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.common.id_utils import generate_id
from app.modules.congregations.db_models import (
    CongregationAddressDB,
    CongregationContactPersonDB,
    CongregationServiceTimeDB,
)

logger = logging.getLogger(__name__)


class CongregationRepository:
    """Data access layer for congregation addresses, service times, and contact persons."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Address operations
    async def get_address_by_tenant_id(
        self, tenant_id: str
    ) -> CongregationAddressDB | None:
        """Get address for a tenant."""
        stmt = select(CongregationAddressDB).where(
            CongregationAddressDB.tenant_id == tenant_id
        )
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
        country: str = "Poland",
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

    async def delete_address(self, tenant_id: str) -> None:
        """Delete address for a tenant."""
        address = await self.get_address_by_tenant_id(tenant_id)
        if address:
            await self.db.delete(address)
            await self.db.commit()

    # Service times operations
    async def get_service_times_by_tenant_id(
        self, tenant_id: str
    ) -> List[CongregationServiceTimeDB]:
        """Get all service times for a tenant."""
        stmt = (
            select(CongregationServiceTimeDB)
            .where(CongregationServiceTimeDB.tenant_id == tenant_id)
            .order_by(
                CongregationServiceTimeDB.order, CongregationServiceTimeDB.created_at
            )
        )
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
        stmt = select(CongregationServiceTimeDB).where(
            CongregationServiceTimeDB.tenant_id == tenant_id
        )
        result = await self.db.execute(stmt)
        service_times = result.scalars().all()
        for st in service_times:
            await self.db.delete(st)
        await self.db.commit()

    # Contact persons operations
    async def get_contact_persons_by_tenant_id(
        self, tenant_id: str
    ) -> List[CongregationContactPersonDB]:
        """Get all contact persons for a tenant."""
        stmt = (
            select(CongregationContactPersonDB)
            .where(CongregationContactPersonDB.tenant_id == tenant_id)
            .order_by(
                CongregationContactPersonDB.order,
                CongregationContactPersonDB.created_at,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_contact_person(
        self,
        tenant_id: str,
        *,
        name: str,
        title: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        order: int = 0,
    ) -> CongregationContactPersonDB:
        """Create a contact person for a tenant."""
        contact_person = CongregationContactPersonDB(
            id=generate_id(),
            tenant_id=tenant_id,
            name=name,
            title=title,
            email=email,
            phone=phone,
            order=order,
        )
        self.db.add(contact_person)
        await self.db.commit()
        await self.db.refresh(contact_person)
        return contact_person

    async def delete_contact_person(
        self, tenant_id: str, contact_person_id: str
    ) -> bool:
        """Delete a contact person belonging to the given tenant."""
        stmt = select(CongregationContactPersonDB).where(
            CongregationContactPersonDB.id == contact_person_id,
            CongregationContactPersonDB.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        contact_person = result.scalar_one_or_none()
        if not contact_person:
            return False
        await self.db.delete(contact_person)
        await self.db.commit()
        return True

    async def delete_all_contact_persons(self, tenant_id: str) -> None:
        """Delete all contact persons for a tenant."""
        stmt = select(CongregationContactPersonDB).where(
            CongregationContactPersonDB.tenant_id == tenant_id
        )
        result = await self.db.execute(stmt)
        contact_persons = result.scalars().all()
        for cp in contact_persons:
            await self.db.delete(cp)
        await self.db.commit()


def get_congregation_repository(
    db: AsyncSession = Depends(get_db),
) -> CongregationRepository:
    """FastAPI dependency to obtain a congregation repository."""
    return CongregationRepository(db)
