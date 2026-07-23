"""Migration: Church hierarchy — communities, regions, churches, services, aliases.

Usage:
    python migrations/056_create_church_hierarchy.py upgrade
    python migrations/056_create_church_hierarchy.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Creating church hierarchy tables...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS communities (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(100) NOT NULL UNIQUE,
                    visibility VARCHAR(32) NOT NULL DEFAULT 'hidden',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """))

        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS regions (
                    id VARCHAR(36) PRIMARY KEY,
                    community_id VARCHAR(36) NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(100) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (community_id, slug)
                )
                """))

        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS churches (
                    id VARCHAR(36) PRIMARY KEY,
                    community_id VARCHAR(36) NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
                    region_id VARCHAR(36) REFERENCES regions(id) ON DELETE SET NULL,
                    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    visibility VARCHAR(32) NOT NULL DEFAULT 'hidden',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """))

        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS branches (
                    id VARCHAR(36) PRIMARY KEY,
                    church_id VARCHAR(36) NOT NULL REFERENCES churches(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(100) NOT NULL,
                    visibility VARCHAR(32) NOT NULL DEFAULT 'hidden',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (church_id, slug)
                )
                """))

        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS persons (
                    id VARCHAR(36) PRIMARY KEY,
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    email VARCHAR(255),
                    phone VARCHAR(50),
                    user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """))

        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS service_types (
                    id VARCHAR(36) PRIMARY KEY,
                    slug VARCHAR(100) NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    scope_type VARCHAR(32) NOT NULL,
                    suggested_role VARCHAR(64),
                    is_senior_tier BOOLEAN NOT NULL DEFAULT FALSE,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    is_system BOOLEAN NOT NULL DEFAULT FALSE,
                    probation_supported BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """))

        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS service_assignments (
                    id VARCHAR(36) PRIMARY KEY,
                    person_id VARCHAR(36) NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
                    service_type_id VARCHAR(36) REFERENCES service_types(id) ON DELETE SET NULL,
                    custom_service_name VARCHAR(255),
                    description TEXT,
                    scope_type VARCHAR(32) NOT NULL,
                    scope_id VARCHAR(36) NOT NULL,
                    started_at TIMESTAMPTZ,
                    ended_at TIMESTAMPTZ,
                    probation_ends_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """))

        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS church_slug_aliases (
                    id VARCHAR(36) PRIMARY KEY,
                    church_id VARCHAR(36) NOT NULL REFERENCES churches(id) ON DELETE CASCADE,
                    alias_type VARCHAR(32) NOT NULL,
                    country_slug VARCHAR(100) NOT NULL,
                    city_slug VARCHAR(100) NOT NULL,
                    slug VARCHAR(255) NOT NULL,
                    is_canonical BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (country_slug, city_slug, slug)
                )
                """))

        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS city_aliases (
                    id VARCHAR(36) PRIMARY KEY,
                    country_slug VARCHAR(100) NOT NULL,
                    alias_slug VARCHAR(100) NOT NULL,
                    city_slug VARCHAR(100) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (country_slug, alias_slug)
                )
                """))

        for stmt in (
            "CREATE INDEX IF NOT EXISTS idx_churches_tenant_id ON churches(tenant_id)",
            "CREATE INDEX IF NOT EXISTS idx_churches_region_id ON churches(region_id)",
            "CREATE INDEX IF NOT EXISTS idx_churches_community_id ON churches(community_id)",
            "CREATE INDEX IF NOT EXISTS idx_branches_church_id ON branches(church_id)",
            "CREATE INDEX IF NOT EXISTS idx_persons_email ON persons(email)",
            "CREATE INDEX IF NOT EXISTS idx_service_assignments_scope ON service_assignments(scope_type, scope_id)",
            "CREATE INDEX IF NOT EXISTS idx_service_assignments_person ON service_assignments(person_id)",
            "CREATE INDEX IF NOT EXISTS idx_church_slug_aliases_church ON church_slug_aliases(church_id)",
            "ALTER TABLE congregation_addresses ADD COLUMN IF NOT EXISTS church_id VARCHAR(36) REFERENCES churches(id) ON DELETE CASCADE",
            "ALTER TABLE congregation_service_times ADD COLUMN IF NOT EXISTS church_id VARCHAR(36) REFERENCES churches(id) ON DELETE CASCADE",
            "ALTER TABLE congregation_contact_persons ADD COLUMN IF NOT EXISTS church_id VARCHAR(36) REFERENCES churches(id) ON DELETE CASCADE",
            "CREATE INDEX IF NOT EXISTS idx_congregation_addresses_church_id ON congregation_addresses(church_id)",
            "CREATE INDEX IF NOT EXISTS idx_congregation_service_times_church_id ON congregation_service_times(church_id)",
            "CREATE INDEX IF NOT EXISTS idx_congregation_contact_persons_church_id ON congregation_contact_persons(church_id)",
        ):
            await conn.execute(text(stmt))

    print("✓ Church hierarchy tables created")


async def downgrade() -> None:
    print("Dropping church hierarchy tables...")

    async with engine.begin() as conn:
        for stmt in (
            "ALTER TABLE congregation_contact_persons DROP COLUMN IF EXISTS church_id",
            "ALTER TABLE congregation_service_times DROP COLUMN IF EXISTS church_id",
            "ALTER TABLE congregation_addresses DROP COLUMN IF EXISTS church_id",
            "DROP TABLE IF EXISTS city_aliases",
            "DROP TABLE IF EXISTS church_slug_aliases",
            "DROP TABLE IF EXISTS service_assignments",
            "DROP TABLE IF EXISTS service_types",
            "DROP TABLE IF EXISTS persons",
            "DROP TABLE IF EXISTS branches",
            "DROP TABLE IF EXISTS churches",
            "DROP TABLE IF EXISTS regions",
            "DROP TABLE IF EXISTS communities",
        ):
            await conn.execute(text(stmt))

    print("✓ Church hierarchy tables dropped")


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Church hierarchy migration")
    parser.add_argument("action", choices=["upgrade", "downgrade"])
    args = parser.parse_args()

    if args.action == "upgrade":
        await upgrade()
    else:
        await downgrade()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
