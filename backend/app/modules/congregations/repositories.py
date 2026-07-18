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
from app.modules.congregations.email_import_db_models import CongregationChangeLogDB
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
        website: str | None = None,
        email: str | None = None,
        iban: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        status: str = "draft",
    ) -> CongregationAddressDB:
        """Create or update address for a tenant.

        latitude/longitude given here are treated as human-approved (typed in
        manually, dragged on the map, or accepted from a geocode preview in
        the edit form) and marked geocode_status="manual"; omitting them
        leaves geocode_status="pending" (no coordinates yet).
        """
        encoded_lat = str(latitude) if latitude is not None else None
        encoded_lng = str(longitude) if longitude is not None else None
        geocode_status = "manual" if latitude is not None or longitude is not None else "pending"

        existing = await self.get_address_by_tenant_id(tenant_id)
        if existing:
            existing.street = street
            existing.city = city
            existing.postal_code = postal_code
            existing.province = province
            existing.country = country
            existing.website = website
            existing.email = email
            existing.iban = iban
            existing.latitude = encoded_lat
            existing.longitude = encoded_lng
            existing.geocode_status = geocode_status
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
            website=website,
            email=email,
            iban=iban,
            latitude=encoded_lat,
            longitude=encoded_lng,
            geocode_status=geocode_status,
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

    async def get_change_log(self, tenant_id: str) -> list[CongregationChangeLogDB]:
        stmt = select(CongregationChangeLogDB).where(CongregationChangeLogDB.tenant_id == tenant_id).order_by(CongregationChangeLogDB.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def log_changes(
        self,
        tenant_id: str,
        *,
        section: str,
        changes: dict[str, tuple[str | None, str | None]],
        source: str,
        actor_label: str,
        actor_user_id: str | None = None,
        actor_person_id: str | None = None,
    ) -> None:
        """Append one change-log row per changed field. No-op (no commit) if `changes` is empty."""
        if not changes:
            return
        for field, (old_value, new_value) in changes.items():
            self.db.add(
                CongregationChangeLogDB(
                    id=generate_id(),
                    tenant_id=tenant_id,
                    section=section,
                    field=field,
                    old_value=old_value,
                    new_value=new_value,
                    source=source,
                    actor_label=actor_label,
                    actor_user_id=actor_user_id,
                    actor_person_id=actor_person_id,
                )
            )
        await self.db.commit()

    async def get_addresses_by_status(self, statuses: Sequence[str]) -> dict[str, CongregationAddressDB]:
        """Get addresses with any of the given statuses, keyed by tenant id."""
        stmt = select(CongregationAddressDB).where(CongregationAddressDB.status.in_(statuses))
        result = await self.db.execute(stmt)
        return {address.tenant_id: address for address in result.scalars()}

    async def get_addresses_for_tenants(self, tenant_ids: Sequence[str]) -> dict[str, CongregationAddressDB]:
        """Get addresses for many tenants at once, keyed by tenant id, regardless of status."""
        if not tenant_ids:
            return {}
        stmt = select(CongregationAddressDB).where(CongregationAddressDB.tenant_id.in_(tenant_ids))
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
    async def get_service_time_by_id(self, tenant_id: str, service_time_id: str) -> CongregationServiceTimeDB | None:
        """Get a single service time belonging to the given tenant."""
        stmt = select(CongregationServiceTimeDB).where(
            CongregationServiceTimeDB.id == service_time_id,
            CongregationServiceTimeDB.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

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
        description: str | None = None,
    ) -> CongregationServiceTimeDB:
        """Create a service time for a tenant."""
        service_time = CongregationServiceTimeDB(
            id=generate_id(),
            tenant_id=tenant_id,
            day=day,
            time=time,
            description=description,
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
