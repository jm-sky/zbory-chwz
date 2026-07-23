"""Migration: Display order for service assignments.

Usage:
    python migrations/063_service_assignment_sort_order.py upgrade
    python migrations/063_service_assignment_sort_order.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Adding sort_order to service_assignments...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0
                """))

        # Copy order from legacy contact persons where backfill linked them.
        await conn.execute(text("""
                UPDATE service_assignments sa
                SET sort_order = cp."order"
                FROM congregation_contact_persons cp
                WHERE sa.source_contact_person_id = cp.id
                """))

        # Remaining rows: preserve previous display order per church scope.
        await conn.execute(text("""
                UPDATE service_assignments sa
                SET sort_order = ranked.row_num - 1
                FROM (
                    SELECT
                        sa2.id,
                        ROW_NUMBER() OVER (
                            PARTITION BY sa2.scope_type, sa2.scope_id
                            ORDER BY
                                COALESCE(st.sort_order, 9999),
                                sa2.created_at
                        ) AS row_num
                    FROM service_assignments sa2
                    LEFT JOIN service_types st ON st.id = sa2.service_type_id
                    WHERE sa2.source_contact_person_id IS NULL
                ) ranked
                WHERE sa.id = ranked.id
                  AND sa.source_contact_person_id IS NULL
                """))

    print("Migration 063 upgrade complete.")


async def downgrade() -> None:
    print("Removing sort_order from service_assignments...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE service_assignments
                DROP COLUMN IF EXISTS sort_order
                """))

    print("Migration 063 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
