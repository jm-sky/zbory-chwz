"""Migration: user_permissions table for ACL allow/deny overrides.

Usage:
    python migrations/078_user_permissions.py upgrade
    python migrations/078_user_permissions.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Creating user_permissions table...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_permissions (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    scope_type VARCHAR(32) NOT NULL,
                    scope_id VARCHAR(36) NOT NULL,
                    permission VARCHAR(64) NOT NULL,
                    effect VARCHAR(8) NOT NULL,
                    source_assignment_id VARCHAR(36) REFERENCES service_assignments(id) ON DELETE CASCADE,
                    created_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (user_id, scope_type, scope_id, permission)
                )
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_user_permissions_user_id
                ON user_permissions (user_id)
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_user_permissions_source_assignment_id
                ON user_permissions (source_assignment_id)
                """))

    print("Migration 078 upgrade complete.")


async def downgrade() -> None:
    print("Dropping user_permissions table...")

    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS user_permissions"))

    print("Migration 078 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
