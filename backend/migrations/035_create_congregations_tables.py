"""Migration: Create congregations tables (addresses, service times, contact persons).

This migration creates tables for congregation addresses, service times,
and contact persons.

Usage:
    python migrations/035_create_congregations_tables.py upgrade
    python migrations/035_create_congregations_tables.py downgrade
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text


async def upgrade() -> None:
    """Create congregations tables."""
    print("Creating congregations tables...")

    async with engine.begin() as conn:
        # Create congregation_addresses table
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS congregation_addresses (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    street VARCHAR(255),
                    city VARCHAR(255) NOT NULL,
                    postal_code VARCHAR(20),
                    province VARCHAR(100),
                    country VARCHAR(100) NOT NULL DEFAULT 'Poland',
                    status VARCHAR(32) NOT NULL DEFAULT 'draft',
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                )
                """
            )
        )

        # Create congregation_service_times table
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS congregation_service_times (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    day VARCHAR(50) NOT NULL,
                    time VARCHAR(10) NOT NULL,
                    "order" INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                )
                """
            )
        )

        # Create congregation_contact_persons table
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS congregation_contact_persons (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    title VARCHAR(100),
                    email VARCHAR(255),
                    phone VARCHAR(50),
                    "order" INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                )
                """
            )
        )

        # Create indexes
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_congregation_addresses_tenant_id ON congregation_addresses(tenant_id)"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_congregation_service_times_tenant_id ON congregation_service_times(tenant_id)"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_congregation_contact_persons_tenant_id ON congregation_contact_persons(tenant_id)"
            )
        )

    print("✓ Congregations tables created successfully")


async def downgrade() -> None:
    """Drop congregations tables."""
    print("Dropping congregations tables...")

    async with engine.begin() as conn:
        # Drop tables in reverse order (due to foreign keys)
        await conn.execute(text("DROP TABLE IF EXISTS congregation_contact_persons"))
        await conn.execute(text("DROP TABLE IF EXISTS congregation_service_times"))
        await conn.execute(text("DROP TABLE IF EXISTS congregation_addresses"))

    print("✓ Congregations tables dropped successfully")


async def main() -> None:
    """Run migration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create congregations tables migration"
    )
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade"],
        help="Migration action (upgrade or downgrade)",
    )
    args = parser.parse_args()

    if args.action == "upgrade":
        await upgrade()
    elif args.action == "downgrade":
        await downgrade()

    # Close database connections
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
