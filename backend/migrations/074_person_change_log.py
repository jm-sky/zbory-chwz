"""Migration: Person change history (`person_change_log`).

Tracks field-level edits to a person's directory record (first/last name,
e-mail, phone). old_value/new_value are TEXT so the app-level EncryptedString
type can transparently encrypt them at rest, matching how the source
`persons` columns themselves are protected.

Usage:
    python migrations/074_person_change_log.py upgrade
    python migrations/074_person_change_log.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Creating person_change_log table...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS person_change_log (
                    id VARCHAR(36) PRIMARY KEY,
                    person_id VARCHAR(36) NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
                    field VARCHAR(32) NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    source VARCHAR(32) NOT NULL,
                    actor_label VARCHAR(255) NOT NULL,
                    actor_user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_person_change_log_person_id_created_at
                ON person_change_log (person_id, created_at DESC)
                """))

    print("Migration 074 upgrade complete.")


async def downgrade() -> None:
    print("Dropping person_change_log table...")

    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS person_change_log"))

    print("Migration 074 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
