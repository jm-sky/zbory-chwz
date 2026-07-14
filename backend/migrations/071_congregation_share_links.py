"""Migration: Share links for anonymous, time-limited congregation access.

Usage:
    python migrations/071_congregation_share_links.py upgrade
    python migrations/071_congregation_share_links.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Creating congregation_share_links table...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS congregation_share_links (
                    id VARCHAR(36) PRIMARY KEY,
                    token VARCHAR(64) NOT NULL UNIQUE,
                    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    created_by_user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
                    visibility_level VARCHAR(16) NOT NULL,
                    label VARCHAR(255),
                    expires_at TIMESTAMPTZ NOT NULL,
                    revoked_at TIMESTAMPTZ,
                    last_used_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    CONSTRAINT ck_congregation_share_links_visibility_level
                        CHECK (visibility_level IN ('public', 'authenticated'))
                )
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_congregation_share_links_tenant_active
                ON congregation_share_links (tenant_id, revoked_at)
                """))

    print("Migration 071 upgrade complete.")


async def downgrade() -> None:
    print("Dropping congregation_share_links table...")

    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS congregation_share_links"))

    print("Migration 071 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
