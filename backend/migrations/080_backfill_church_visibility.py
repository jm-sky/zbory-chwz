"""Migration: backfill churches.visibility from congregation address status.

Usage:
    python migrations/080_backfill_church_visibility.py upgrade
    python migrations/080_backfill_church_visibility.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, select, update

from app.core.database import AsyncSessionLocal
from app.modules.churches.db_models import ChurchDB
from app.modules.congregations.db_models import CongregationAddressDB

PUBLIC_STATUSES = ("published", "published_unverified")
HIDDEN_STATUSES = ("draft", "need_verification")


async def upgrade() -> None:
    print("Backfilling churches.visibility from address status...")

    async with AsyncSessionLocal() as db:
        before_public = await db.scalar(select(func.count()).select_from(ChurchDB).where(ChurchDB.visibility == "public"))
        print(f"  churches.visibility=public before: {before_public}")

        churches = (await db.execute(select(ChurchDB))).scalars().all()
        public_count = 0
        hidden_count = 0

        for church in churches:
            address_result = await db.execute(select(CongregationAddressDB).where(CongregationAddressDB.tenant_id == church.id))
            address = address_result.scalar_one_or_none()
            if address and address.status in PUBLIC_STATUSES:
                church.visibility = "public"
                public_count += 1
            else:
                church.visibility = "hidden"
                hidden_count += 1

        await db.commit()

        after_public = await db.scalar(select(func.count()).select_from(ChurchDB).where(ChurchDB.visibility == "public"))
        print(f"  Set public: {public_count}, hidden: {hidden_count}")
        print(f"  churches.visibility=public after: {after_public}")

    print("Migration 080 upgrade complete.")


async def downgrade() -> None:
    print("Resetting churches.visibility to hidden...")

    async with AsyncSessionLocal() as db:
        await db.execute(update(ChurchDB).values(visibility="hidden"))
        await db.commit()

    print("Migration 080 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
