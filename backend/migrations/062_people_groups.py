"""Migration: People groups (organizational groups independent of a single church).

See docs/plans/2026-07-09--people-groups.md.

Usage:
    python migrations/062_people_groups.py upgrade
    python migrations/062_people_groups.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Creating people_groups tables...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS people_groups (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    slug VARCHAR(255) NOT NULL UNIQUE,
                    description TEXT NULL,
                    scope_type VARCHAR(32) NOT NULL DEFAULT 'global',
                    scope_id VARCHAR(36) NULL,
                    visibility VARCHAR(32) NOT NULL DEFAULT 'authenticated',
                    steward_user_id VARCHAR(36) NULL REFERENCES users(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """))
        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS people_group_memberships (
                    id VARCHAR(36) PRIMARY KEY,
                    group_id VARCHAR(36) NOT NULL REFERENCES people_groups(id) ON DELETE CASCADE,
                    person_id VARCHAR(36) NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
                    role_label VARCHAR(255) NULL,
                    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    left_at TIMESTAMPTZ NULL
                )
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_people_group_memberships_group_id
                ON people_group_memberships (group_id)
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_people_group_memberships_person_id
                ON people_group_memberships (person_id)
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_people_groups_steward_user_id
                ON people_groups (steward_user_id)
                """))

    print("Migration 062 upgrade complete.")


async def downgrade() -> None:
    print("Dropping people_groups tables...")

    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS people_group_memberships"))
        await conn.execute(text("DROP TABLE IF EXISTS people_groups"))

    print("Migration 062 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
