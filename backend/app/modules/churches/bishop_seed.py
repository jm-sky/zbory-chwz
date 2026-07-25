"""Seed bishop service assignments and ACL roles."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.modules.auth.db_models import UserDB
from app.modules.churches.acl_models import UserRoleAssignmentDB
from app.modules.churches.acl_seed import ensure_acl_roles, resolve_acl_scope
from app.modules.churches.db_models import (
    CommunityDB,
    PersonDB,
    RegionDB,
    ServiceAssignmentDB,
    ServiceTypeDB,
)
from app.modules.churches.seed_data import CHWZ_COMMUNITY_SLUG

logger = logging.getLogger(__name__)

BISHOP_SEED: list[dict[str, str | None]] = [
    {
        "email": "roman.jawdyk@chwz.org.pl",
        "first_name": "Roman",
        "last_name": "Jawdyk",
        "service_slug": "biskup_naczelny",
        "role_name": "bishop",
        "region_slug": None,
    },
    {
        "email": "bellux@op.pl",
        "first_name": "Leszek",
        "last_name": "Bijak",
        "service_slug": "biskup_regionu",
        "role_name": "regional_bishop",
        "region_slug": "centralny",
    },
    {
        "email": "jacek.romanowski@chwz.org.pl",
        "first_name": "Jacek",
        "last_name": "Romanowski",
        "service_slug": "biskup_regionu",
        "role_name": "regional_bishop",
        "region_slug": "polnocno-wschodni",
    },
    {
        "email": "pandre@poczta.onet.pl",
        "first_name": "Andrzej",
        "last_name": "Poręba",
        "service_slug": "biskup_regionu",
        "role_name": "regional_bishop",
        "region_slug": "gorny-slask",
    },
]


async def ensure_pastor_acl_for_owner(
    db: AsyncSession,
    *,
    user_id: str,
    church_id: str,
) -> None:
    roles_by_name = await ensure_acl_roles(db)
    pastor_role = roles_by_name.get("pastor")
    if not pastor_role:
        return

    existing = await db.execute(
        select(UserRoleAssignmentDB).where(
            UserRoleAssignmentDB.user_id == user_id,
            UserRoleAssignmentDB.role_id == pastor_role.id,
            UserRoleAssignmentDB.scope_type == "church",
            UserRoleAssignmentDB.scope_id == church_id,
        )
    )
    if existing.scalar_one_or_none():
        return

    db.add(
        UserRoleAssignmentDB(
            id=generate_id(),
            user_id=user_id,
            role_id=pastor_role.id,
            scope_type="church",
            scope_id=church_id,
            source_assignment_id=None,
        )
    )
    await db.flush()


async def seed_bishops(db: AsyncSession) -> int:
    """Idempotent bishop persons, service assignments, and ACL grants."""
    community_result = await db.execute(select(CommunityDB).where(CommunityDB.slug == CHWZ_COMMUNITY_SLUG))
    community = community_result.scalar_one_or_none()
    if not community:
        logger.warning("CHWZ community missing — skip bishop seed")
        return 0

    regions_result = await db.execute(select(RegionDB).where(RegionDB.community_id == community.id))
    regions_by_slug = {r.slug: r for r in regions_result.scalars().all()}

    roles_by_name = await ensure_acl_roles(db)
    service_types_result = await db.execute(select(ServiceTypeDB))
    service_types_by_slug = {st.slug: st for st in service_types_result.scalars().all()}

    seeded = 0
    for entry in BISHOP_SEED:
        email = entry["email"].lower().strip()
        user_result = await db.execute(select(UserDB).where(UserDB.email == email))
        user = user_result.scalar_one_or_none()
        if not user:
            logger.warning("Bishop seed: user %s not found", email)
            continue

        person_result = await db.execute(select(PersonDB).where(PersonDB.user_id == user.id))
        person = person_result.scalar_one_or_none()
        if not person:
            person = PersonDB(
                id=generate_id(),
                first_name=entry["first_name"],
                last_name=entry["last_name"],
                email=email,
                user_id=user.id,
            )
            db.add(person)
            await db.flush()

        service_type = service_types_by_slug.get(entry["service_slug"])
        if not service_type:
            logger.warning("Bishop seed: service type %s missing", entry["service_slug"])
            continue

        region_slug = entry["region_slug"]
        if region_slug:
            region = regions_by_slug.get(region_slug)
            if not region:
                logger.warning("Bishop seed: region %s missing", region_slug)
                continue
            scope_type = "region"
            scope_id = region.id
            region_id = region.id
        else:
            scope_type = "community"
            scope_id = community.id
            region_id = None

        assignment_result = await db.execute(
            select(ServiceAssignmentDB).where(
                ServiceAssignmentDB.person_id == person.id,
                ServiceAssignmentDB.service_type_id == service_type.id,
                ServiceAssignmentDB.scope_type == scope_type,
                ServiceAssignmentDB.scope_id == scope_id,
            )
        )
        assignment = assignment_result.scalar_one_or_none()
        if not assignment:
            assignment = ServiceAssignmentDB(
                id=generate_id(),
                person_id=person.id,
                service_type_id=service_type.id,
                scope_type=scope_type,
                scope_id=scope_id,
            )
            db.add(assignment)
            await db.flush()
            seeded += 1

        role = roles_by_name.get(entry["role_name"])
        if not role:
            continue

        acl_scope = resolve_acl_scope(
            entry["role_name"],
            church_id="",
            community_id=community.id,
            region_id=region_id,
        )
        if not acl_scope:
            continue
        acl_scope_type, acl_scope_id = acl_scope

        existing_acl = await db.execute(
            select(UserRoleAssignmentDB).where(
                UserRoleAssignmentDB.user_id == user.id,
                UserRoleAssignmentDB.role_id == role.id,
                UserRoleAssignmentDB.scope_type == acl_scope_type,
                UserRoleAssignmentDB.scope_id == acl_scope_id,
            )
        )
        if existing_acl.scalar_one_or_none():
            continue

        db.add(
            UserRoleAssignmentDB(
                id=generate_id(),
                user_id=user.id,
                role_id=role.id,
                scope_type=acl_scope_type,
                scope_id=acl_scope_id,
                source_assignment_id=assignment.id,
            )
        )
        await db.flush()

    return seeded
