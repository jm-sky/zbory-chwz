"""Migration: Visibility flags on service_assignments.

Usage:
    python migrations/057_service_assignment_visibility.py upgrade
    python migrations/057_service_assignment_visibility.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Adding visibility columns to service_assignments...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD COLUMN IF NOT EXISTS show_on_card BOOLEAN NOT NULL DEFAULT TRUE
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD COLUMN IF NOT EXISTS phone_public BOOLEAN NOT NULL DEFAULT TRUE
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD COLUMN IF NOT EXISTS email_public BOOLEAN NOT NULL DEFAULT FALSE
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD COLUMN IF NOT EXISTS source_contact_person_id VARCHAR(36) NULL
                """))

    print("Migration 057 upgrade complete.")


async def downgrade() -> None:
    print("Removing visibility columns from service_assignments...")

    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE service_assignments DROP COLUMN IF EXISTS source_contact_person_id"))
        await conn.execute(text("ALTER TABLE service_assignments DROP COLUMN IF EXISTS email_public"))
        await conn.execute(text("ALTER TABLE service_assignments DROP COLUMN IF EXISTS phone_public"))
        await conn.execute(text("ALTER TABLE service_assignments DROP COLUMN IF EXISTS show_on_card"))

    print("Migration 057 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
