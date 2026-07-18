"""Migration: Add website, email, and iban to congregation_addresses.

- website: TEXT, nullable (Fernet-encrypted at the ORM layer via EncryptedString,
  same as street/city/postal_code/province — stored as ciphertext, so the
  column must be unbounded TEXT rather than a bounded VARCHAR)
- email: TEXT, nullable (same as website)
- iban: TEXT, nullable (same as website; stores the full canonical IBAN,
  always with a country prefix)

Usage:
    python migrations/076_congregation_contact_fields.py upgrade
    python migrations/076_congregation_contact_fields.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Adding website/email/iban columns to congregation_addresses...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                ADD COLUMN IF NOT EXISTS website TEXT
                """))
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                ADD COLUMN IF NOT EXISTS email TEXT
                """))
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                ADD COLUMN IF NOT EXISTS iban TEXT
                """))

    print("Migration 076 upgrade complete.")


async def downgrade() -> None:
    print("Removing website/email/iban columns from congregation_addresses...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                DROP COLUMN IF EXISTS website
                """))
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                DROP COLUMN IF EXISTS email
                """))
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                DROP COLUMN IF EXISTS iban
                """))

    print("Migration 076 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
