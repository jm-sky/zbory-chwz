"""Migration: ACL tables for church platform roles and permissions.

Usage:
    python migrations/059_acl_tables.py upgrade
    python migrations/059_acl_tables.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Creating ACL tables...")

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS roles (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(64) NOT NULL UNIQUE,
                    scope_type VARCHAR(32) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS role_permissions (
                    id VARCHAR(36) PRIMARY KEY,
                    role_id VARCHAR(36) NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                    permission VARCHAR(64) NOT NULL,
                    UNIQUE (role_id, permission)
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_role_assignments (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role_id VARCHAR(36) NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                    scope_type VARCHAR(32) NOT NULL,
                    scope_id VARCHAR(36) NOT NULL,
                    source_assignment_id VARCHAR(36) REFERENCES service_assignments(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (user_id, role_id, scope_type, scope_id)
                )
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_user_role_assignments_user_id
                ON user_role_assignments (user_id)
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_user_role_assignments_source_assignment_id
                ON user_role_assignments (source_assignment_id)
                """
            )
        )

    print("Migration 059 upgrade complete. Run: python -m cli db churches-backfill")


async def downgrade() -> None:
    print("Dropping ACL tables...")

    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS user_role_assignments"))
        await conn.execute(text("DROP TABLE IF EXISTS role_permissions"))
        await conn.execute(text("DROP TABLE IF EXISTS roles"))

    print("Migration 059 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
