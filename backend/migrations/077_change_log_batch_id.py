"""Migration: Add batch_id to congregation_change_log and person_change_log.

Groups field-change rows written by the same action (e.g. one form save that
changes several fields) so the change-history UI can render one tile per
action instead of one per field. Existing rows have no natural grouping, so
each is backfilled as its own singleton batch (batch_id = id).

Usage:
    python migrations/077_change_log_batch_id.py upgrade
    python migrations/077_change_log_batch_id.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Adding batch_id to congregation_change_log and person_change_log...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE congregation_change_log
                ADD COLUMN IF NOT EXISTS batch_id VARCHAR(36)
                """))
        await conn.execute(text("""
                UPDATE congregation_change_log SET batch_id = id WHERE batch_id IS NULL
                """))
        await conn.execute(text("""
                ALTER TABLE congregation_change_log ALTER COLUMN batch_id SET NOT NULL
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_congregation_change_log_tenant_id_batch_id
                ON congregation_change_log (tenant_id, batch_id)
                """))

        await conn.execute(text("""
                ALTER TABLE person_change_log
                ADD COLUMN IF NOT EXISTS batch_id VARCHAR(36)
                """))
        await conn.execute(text("""
                UPDATE person_change_log SET batch_id = id WHERE batch_id IS NULL
                """))
        await conn.execute(text("""
                ALTER TABLE person_change_log ALTER COLUMN batch_id SET NOT NULL
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_person_change_log_person_id_batch_id
                ON person_change_log (person_id, batch_id)
                """))

    print("Migration 077 upgrade complete.")


async def downgrade() -> None:
    print("Removing batch_id from congregation_change_log and person_change_log...")

    async with engine.begin() as conn:
        await conn.execute(text("DROP INDEX IF EXISTS ix_person_change_log_person_id_batch_id"))
        await conn.execute(text("ALTER TABLE person_change_log DROP COLUMN IF EXISTS batch_id"))
        await conn.execute(text("DROP INDEX IF EXISTS ix_congregation_change_log_tenant_id_batch_id"))
        await conn.execute(text("ALTER TABLE congregation_change_log DROP COLUMN IF EXISTS batch_id"))

    print("Migration 077 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
