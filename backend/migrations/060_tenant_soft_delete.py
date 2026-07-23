"""Migration: Soft delete for tenants (congregations).

Hard deleting a tenant fails on the tenant_memberships FK (NO ACTION) and
would cascade churches, addresses and service times away. Congregations are
retired instead of erased.

Usage:
    python migrations/060_tenant_soft_delete.py upgrade
    python migrations/060_tenant_soft_delete.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Adding deleted_at to tenants...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE tenants
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tenants_deleted_at
                ON tenants (deleted_at)
                WHERE deleted_at IS NULL
                """))

    print("Migration 060 upgrade complete.")


async def downgrade() -> None:
    print("Removing deleted_at from tenants...")

    async with engine.begin() as conn:
        await conn.execute(text("DROP INDEX IF EXISTS idx_tenants_deleted_at"))
        await conn.execute(text("ALTER TABLE tenants DROP COLUMN IF EXISTS deleted_at"))

    print("Migration 060 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
