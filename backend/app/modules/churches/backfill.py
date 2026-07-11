"""Backfill church hierarchy from existing tenants."""

import logging

from sqlalchemy import select, update

from app.common.id_utils import generate_id
from app.modules.churches.acl_seed import ensure_acl_roles
from app.modules.churches.db_models import (
    ChurchDB,
    ChurchSlugAliasDB,
    CityAliasDB,
    CommunityDB,
    PersonDB,
    RegionDB,
    ServiceAssignmentDB,
    ServiceTypeDB,
)
from app.modules.churches.seed_data import (
    CHWZ_COMMUNITY_SLUG,
    CHWZ_ORG_TENANT_NAME,
    CITY_ALIASES_SEED,
    CITY_REGION_MAP,
    REGIONS_SEED,
    REMOVED_SERVICE_TYPE_SLUGS,
    SERVICE_TYPE_MIGRATIONS,
    SERVICE_TYPES_SEED,
    TITLE_TO_SERVICE_SLUG,
)
from app.modules.churches.slug_utils import church_slug, city_slug, country_slug
from app.modules.congregations.db_models import (
    CongregationAddressDB,
    CongregationContactPersonDB,
    CongregationServiceTimeDB,
)
from app.modules.churches.repositories import ChurchRepository
from app.modules.tenants.db_models import TenantDB

logger = logging.getLogger(__name__)


async def backfill_churches(repo: ChurchRepository) -> dict[str, int]:
    db = repo.db
    stats = {
        "communities": 0,
        "regions": 0,
        "service_types": 0,
        "city_aliases": 0,
        "org_tenant": 0,
        "churches": 0,
        "slug_aliases": 0,
        "congregation_links": 0,
        "contact_person_migrations": 0,
    }

    community = await _get_or_create_community(db, stats)
    regions_by_slug = await _ensure_regions(db, community.id, stats)
    service_types_by_slug = await _ensure_service_types(db, stats)
    await ensure_acl_roles(db)
    await _ensure_city_aliases(db, stats)
    org_tenant = await _get_or_create_org_tenant(db, stats)

    tenants_result = await db.execute(select(TenantDB).order_by(TenantDB.created_at))
    tenants = list(tenants_result.scalars().all())

    for tenant in tenants:
        existing = await db.execute(select(ChurchDB).where(ChurchDB.id == tenant.id))
        if existing.scalar_one_or_none():
            await _link_congregation_rows(db, tenant.id, stats)
            continue

        region_id = await _resolve_region_for_tenant(db, tenant.id, regions_by_slug)
        church = ChurchDB(
            id=tenant.id,
            community_id=community.id,
            region_id=region_id,
            tenant_id=org_tenant.id,
            name=tenant.name,
            visibility="hidden",
        )
        db.add(church)
        await db.flush()

        address_result = await db.execute(
            select(CongregationAddressDB).where(
                CongregationAddressDB.tenant_id == tenant.id
            )
        )
        address = address_result.scalar_one_or_none()
        if address:
            await _ensure_church_slug_alias(
                db,
                church_id=church.id,
                country=address.country,
                city=address.city,
                name=tenant.name,
                stats=stats,
            )

        await _link_congregation_rows(db, tenant.id, stats)
        stats["churches"] += 1

    await _migrate_contact_persons(db, service_types_by_slug, stats)
    await db.commit()
    return stats


async def _get_or_create_community(db, stats: dict[str, int]) -> CommunityDB:
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
    stats["communities"] += 1
    return community


async def _ensure_regions(
    db, community_id: str, stats: dict[str, int]
) -> dict[str, RegionDB]:
    regions_by_slug: dict[str, RegionDB] = {}
    for item in REGIONS_SEED:
        result = await db.execute(
            select(RegionDB).where(
                RegionDB.community_id == community_id,
                RegionDB.slug == item["slug"],
            )
        )
        region = result.scalar_one_or_none()
        if not region:
            region = RegionDB(
                id=generate_id(),
                community_id=community_id,
                name=item["name"],
                slug=item["slug"],
            )
            db.add(region)
            await db.flush()
            stats["regions"] += 1
        regions_by_slug[item["slug"]] = region
    return regions_by_slug


async def _ensure_service_types(db, stats: dict[str, int]) -> dict[str, ServiceTypeDB]:
    by_slug: dict[str, ServiceTypeDB] = {}
    for slug, name, scope, role, senior, order in SERVICE_TYPES_SEED:
        result = await db.execute(
            select(ServiceTypeDB).where(ServiceTypeDB.slug == slug)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = name
            existing.scope_type = scope
            existing.suggested_role = role
            existing.is_senior_tier = senior
            existing.sort_order = order
            existing.is_system = True
            by_slug[slug] = existing
            continue
        service_type = ServiceTypeDB(
            id=generate_id(),
            slug=slug,
            name=name,
            scope_type=scope,
            suggested_role=role,
            is_senior_tier=senior,
            sort_order=order,
            is_system=True,
        )
        db.add(service_type)
        by_slug[slug] = service_type
        stats["service_types"] += 1

    await _migrate_removed_service_types(db, by_slug, stats)
    await db.flush()
    return by_slug


async def _migrate_removed_service_types(
    db,
    service_types_by_slug: dict[str, ServiceTypeDB],
    stats: dict[str, int],
) -> None:
    for old_slug, new_slug in SERVICE_TYPE_MIGRATIONS.items():
        old_result = await db.execute(
            select(ServiceTypeDB).where(ServiceTypeDB.slug == old_slug)
        )
        old_type = old_result.scalar_one_or_none()
        new_type = service_types_by_slug.get(new_slug)
        if not old_type or not new_type:
            continue
        result = await db.execute(
            update(ServiceAssignmentDB)
            .where(ServiceAssignmentDB.service_type_id == old_type.id)
            .values(service_type_id=new_type.id)
        )
        stats["service_assignments_migrated"] = stats.get("service_assignments_migrated", 0) + (
            result.rowcount or 0
        )

    for slug in REMOVED_SERVICE_TYPE_SLUGS:
        result = await db.execute(
            select(ServiceTypeDB).where(ServiceTypeDB.slug == slug)
        )
        service_type = result.scalar_one_or_none()
        if not service_type:
            continue
        await db.delete(service_type)
        service_types_by_slug.pop(slug, None)
        stats["service_types_removed"] = stats.get("service_types_removed", 0) + 1


async def _ensure_church_slug_alias(
    db,
    *,
    church_id: str,
    country: str,
    city: str,
    name: str,
    stats: dict[str, int],
) -> None:
    c_slug = country_slug(country)
    ci_slug = city_slug(city)
    s_slug = church_slug(name)

    existing_path = await db.execute(
        select(ChurchSlugAliasDB).where(
            ChurchSlugAliasDB.country_slug == c_slug,
            ChurchSlugAliasDB.city_slug == ci_slug,
            ChurchSlugAliasDB.slug == s_slug,
        )
    )
    if existing_path.scalar_one_or_none():
        return

    existing_canonical = await db.execute(
        select(ChurchSlugAliasDB).where(
            ChurchSlugAliasDB.church_id == church_id,
            ChurchSlugAliasDB.is_canonical.is_(True),
        )
    )
    if existing_canonical.scalar_one_or_none():
        return

    db.add(
        ChurchSlugAliasDB(
            id=generate_id(),
            church_id=church_id,
            alias_type="canonical",
            country_slug=c_slug,
            city_slug=ci_slug,
            slug=s_slug,
            is_canonical=True,
        )
    )
    stats["slug_aliases"] += 1
    await db.flush()


async def _ensure_city_aliases(db, stats: dict[str, int]) -> None:
    for item in CITY_ALIASES_SEED:
        result = await db.execute(
            select(CityAliasDB).where(
                CityAliasDB.country_slug == item["country_slug"],
                CityAliasDB.alias_slug == item["alias_slug"],
            )
        )
        if result.scalar_one_or_none():
            continue
        db.add(
            CityAliasDB(
                id=generate_id(),
                country_slug=item["country_slug"],
                alias_slug=item["alias_slug"],
                city_slug=item["city_slug"],
            )
        )
        stats["city_aliases"] += 1
    await db.flush()


async def _get_or_create_org_tenant(db, stats: dict[str, int]) -> TenantDB:
    result = await db.execute(
        select(TenantDB).where(TenantDB.name == CHWZ_ORG_TENANT_NAME)
    )
    org = result.scalar_one_or_none()
    if org:
        return org

    any_tenant = await db.execute(select(TenantDB).limit(1))
    first = any_tenant.scalar_one_or_none()
    owner_id = first.owner_id if first else None
    if not owner_id:
        from app.modules.auth.db_models import UserDB

        user_result = await db.execute(select(UserDB).limit(1))
        user = user_result.scalar_one_or_none()
        if not user:
            raise RuntimeError("No users in database — cannot create org tenant")
        owner_id = user.id

    org = TenantDB(
        id=generate_id(),
        name=CHWZ_ORG_TENANT_NAME,
        description="CHWZ organizational tenant",
        status="published",
        owner_id=owner_id,
    )
    db.add(org)
    await db.flush()
    stats["org_tenant"] += 1
    return org


async def _resolve_region_for_tenant(
    db, tenant_id: str, regions_by_slug: dict[str, RegionDB]
) -> str | None:
    result = await db.execute(
        select(CongregationAddressDB).where(
            CongregationAddressDB.tenant_id == tenant_id
        )
    )
    address = result.scalar_one_or_none()
    if not address:
        return None
    key = city_slug(address.city)
    region_slug = CITY_REGION_MAP.get(key) or CITY_REGION_MAP.get(address.city.lower())
    if not region_slug:
        return None
    region = regions_by_slug.get(region_slug)
    return region.id if region else None


def _split_person_name(full_name: str) -> tuple[str | None, str | None]:
    parts = full_name.strip().split(None, 1)
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


def _resolve_service_type_for_title(
    title: str | None, service_types_by_slug: dict[str, ServiceTypeDB]
) -> tuple[str | None, str | None]:
    if not title:
        return None, None
    normalized = title.strip().lower()
    slug = TITLE_TO_SERVICE_SLUG.get(normalized)
    if slug and slug in service_types_by_slug:
        return service_types_by_slug[slug].id, None
    return None, title.strip()


async def _migrate_contact_persons(
    db, service_types_by_slug: dict[str, ServiceTypeDB], stats: dict[str, int]
) -> None:
    result = await db.execute(select(CongregationContactPersonDB))
    contact_persons = list(result.scalars().all())

    for cp in contact_persons:
        already = await db.execute(
            select(ServiceAssignmentDB).where(
                ServiceAssignmentDB.source_contact_person_id == cp.id
            )
        )
        if already.scalar_one_or_none():
            continue

        church_id = cp.church_id or cp.tenant_id
        first_name, last_name = _split_person_name(cp.name)
        service_type_id, custom_name = _resolve_service_type_for_title(
            cp.title, service_types_by_slug
        )

        person = PersonDB(
            id=generate_id(),
            first_name=first_name,
            last_name=last_name,
            email=cp.email,
            phone=cp.phone,
        )
        db.add(person)
        await db.flush()

        assignment = ServiceAssignmentDB(
            id=generate_id(),
            person_id=person.id,
            service_type_id=service_type_id,
            custom_service_name=custom_name,
            description=None,
            scope_type="church",
            scope_id=church_id,
            card_visibility="public",
            phone_visibility="public" if cp.phone else "hidden",
            email_visibility="public" if cp.email else "hidden",
            source_contact_person_id=cp.id,
            sort_order=cp.order,
        )
        db.add(assignment)
        stats["contact_person_migrations"] += 1

    await db.flush()


async def _link_congregation_rows(db, church_id: str, stats: dict[str, int]) -> None:
    for model in (
        CongregationAddressDB,
        CongregationServiceTimeDB,
        CongregationContactPersonDB,
    ):
        await db.execute(
            update(model)
            .where(model.tenant_id == church_id)
            .values(church_id=church_id)
        )
    stats["congregation_links"] += 1
