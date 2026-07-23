"""Migration: Refresh system service types (names, order, new types, removed legacy).

Usage:
    python migrations/064_update_service_types.py upgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.modules.churches.backfill import _ensure_service_types


async def upgrade() -> None:
    print("Updating system service types...")

    async with AsyncSessionLocal() as session:
        stats: dict[str, int] = {"service_types": 0}
        await _ensure_service_types(session, stats)
        await session.commit()
        print(
            "Migration 064 upgrade complete:",
            f"created={stats.get('service_types', 0)},",
            f"migrated_assignments={stats.get('service_assignments_migrated', 0)},",
            f"removed={stats.get('service_types_removed', 0)}",
        )


async def downgrade() -> None:
    print("Migration 064 has no downgrade — service type labels are data, not schema.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
