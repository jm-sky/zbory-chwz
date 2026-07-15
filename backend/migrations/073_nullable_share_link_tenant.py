"""Migration: Allow congregation share links without a tenant (all-congregations links).

A NULL tenant_id marks a link created by an admin/owner that resolves to every
published congregation they can see, instead of a single congregation.

Usage:
    python migrations/073_nullable_share_link_tenant.py upgrade
    python migrations/073_nullable_share_link_tenant.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Making congregation_share_links.tenant_id nullable...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE congregation_share_links
                ALTER COLUMN tenant_id DROP NOT NULL
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_congregation_share_links_creator_active
                ON congregation_share_links (created_by_user_id, revoked_at)
                WHERE tenant_id IS NULL
                """))

    print("Migration 073 upgrade complete.")


async def downgrade() -> None:
    print("Restoring congregation_share_links.tenant_id NOT NULL constraint...")

    async with engine.begin() as conn:
        await conn.execute(text("DROP INDEX IF EXISTS ix_congregation_share_links_creator_active"))
        await conn.execute(text("DELETE FROM congregation_share_links WHERE tenant_id IS NULL"))
        await conn.execute(text("""
                ALTER TABLE congregation_share_links
                ALTER COLUMN tenant_id SET NOT NULL
                """))

    print("Migration 073 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
