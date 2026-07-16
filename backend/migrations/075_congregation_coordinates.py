"""Migration: Add GPS coordinates to congregation_addresses.

- latitude: TEXT, nullable (Fernet-encrypted at the ORM layer via EncryptedString,
  same as street/city/postal_code/province — stored as ciphertext, so the
  column must be unbounded TEXT rather than a numeric type)
- longitude: TEXT, nullable (same as latitude)
- geocode_status: VARCHAR(16), not null, default 'pending' (pending|manual)
  — plain column, not PII, tracks whether coordinates have been set

Usage:
    python migrations/075_congregation_coordinates.py upgrade
    python migrations/075_congregation_coordinates.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Adding latitude/longitude/geocode_status columns to congregation_addresses...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                ADD COLUMN IF NOT EXISTS latitude TEXT
                """))
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                ADD COLUMN IF NOT EXISTS longitude TEXT
                """))
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                ADD COLUMN IF NOT EXISTS geocode_status VARCHAR(16) NOT NULL DEFAULT 'pending'
                """))

    print("Migration 075 upgrade complete.")


async def downgrade() -> None:
    print("Removing latitude/longitude/geocode_status columns from congregation_addresses...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                DROP COLUMN IF EXISTS latitude
                """))
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                DROP COLUMN IF EXISTS longitude
                """))
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                DROP COLUMN IF EXISTS geocode_status
                """))

    print("Migration 075 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
