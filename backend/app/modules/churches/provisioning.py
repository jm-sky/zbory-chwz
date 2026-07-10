"""Create the church hierarchy row that backs a newly created tenant.

`backfill.py` does this for tenants that predate the hierarchy. This module
does it for tenants created at runtime, so a fresh congregation immediately
has working branches, people and service assignments.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.modules.churches.db_models import ChurchDB, CommunityDB
from app.modules.churches.seed_data import CHWZ_COMMUNITY_SLUG, CHWZ_ORG_TENANT_NAME
from app.modules.tenants.db_models import TenantDB


async def get_or_create_community(db: AsyncSession) -> CommunityDB:
    result = await db.execute(
        select(CommunityDB).where(CommunityDB.slug == CHWZ_COMMUNITY_SLUG)
    )
    community = result.scalar_one_or_none()
    if community:
        return community

    community = CommunityDB(
        id=generate_id(),
        name="CHWZ",
        slug=CHWZ_COMMUNITY_SLUG,
        visibility="hidden",
    )
    db.add(community)
    await db.flush()
    return community


async def get_or_create_org_tenant(db: AsyncSession, owner_user_id: str) -> TenantDB:
    result = await db.execute(
        select(TenantDB).where(TenantDB.name == CHWZ_ORG_TENANT_NAME)
    )
    org = result.scalar_one_or_none()
    if org:
        return org

    org = TenantDB(
        id=generate_id(),
        name=CHWZ_ORG_TENANT_NAME,
        description="CHWZ organizational tenant",
        status="published",
        owner_id=owner_user_id,
    )
    db.add(org)
    await db.flush()
    return org


async def provision_church_for_tenant(db: AsyncSession, tenant: TenantDB) -> ChurchDB:
    """Create the `churches` row for a tenant, reusing the tenant id.

    Idempotent. `region_id` stays NULL — a bishop or admin assigns it later.
    """
    existing = await db.execute(select(ChurchDB).where(ChurchDB.id == tenant.id))
    church = existing.scalar_one_or_none()
    if church:
        return church

    community = await get_or_create_community(db)
    org_tenant = await get_or_create_org_tenant(db, tenant.owner_id)

    church = ChurchDB(
        id=tenant.id,
        community_id=community.id,
        region_id=None,
        tenant_id=org_tenant.id,
        name=tenant.name,
        visibility="hidden",
    )
    db.add(church)
    await db.flush()
    return church
