"""Migration: Add optional description column to congregation_service_times.

- description: free-text label for a service time (e.g. "Modlitwa nocna"), max 256 chars

Usage:
    python migrations/070_service_time_description.py upgrade
    python migrations/070_service_time_description.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Adding description column to congregation_service_times...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE congregation_service_times
                ADD COLUMN IF NOT EXISTS description VARCHAR(256)
                """))

    print("Migration 070 upgrade complete.")


async def downgrade() -> None:
    print("Removing description column from congregation_service_times...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE congregation_service_times
                DROP COLUMN IF EXISTS description
                """))

    print("Migration 070 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
