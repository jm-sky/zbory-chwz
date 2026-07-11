"""Migration: Separate list visibility from profile visibility.

- show_on_list: whether the person appears on the congregation list card
- profile_visibility: renamed from card_visibility (who sees the person on the profile page)

Usage:
    python migrations/065_show_on_list_profile_visibility.py upgrade
    python migrations/065_show_on_list_profile_visibility.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Adding show_on_list and renaming card_visibility to profile_visibility...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD COLUMN IF NOT EXISTS show_on_list BOOLEAN NOT NULL DEFAULT TRUE
                """))
        await conn.execute(text("""
                UPDATE service_assignments
                SET show_on_list = (card_visibility = 'public')
                WHERE show_on_list IS TRUE
                  AND card_visibility IS NOT NULL
                  AND card_visibility != 'public'
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                DROP CONSTRAINT IF EXISTS ck_service_assignments_card_visibility
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                RENAME COLUMN card_visibility TO profile_visibility
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD CONSTRAINT ck_service_assignments_profile_visibility
                CHECK (profile_visibility IN ('hidden', 'public', 'authenticated', 'pastors'))
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ALTER COLUMN phone_visibility SET DEFAULT 'authenticated'
                """))

    print("Migration 065 upgrade complete.")


async def downgrade() -> None:
    print("Reverting show_on_list and profile_visibility rename...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE service_assignments
                DROP CONSTRAINT IF EXISTS ck_service_assignments_profile_visibility
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                RENAME COLUMN profile_visibility TO card_visibility
                """))
        await conn.execute(text("""
                UPDATE service_assignments
                SET card_visibility = 'hidden'
                WHERE show_on_list = FALSE
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD CONSTRAINT ck_service_assignments_card_visibility
                CHECK (card_visibility IN ('hidden', 'public', 'authenticated', 'pastors'))
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                DROP COLUMN IF EXISTS show_on_list
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ALTER COLUMN phone_visibility SET DEFAULT 'public'
                """))

    print("Migration 065 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
