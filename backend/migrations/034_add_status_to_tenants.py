"""Migration: Add status column to tenants table.

This migration adds status column to the tenants table to support
draft/published status for congregations.

Usage:
    python migrations/034_add_status_to_tenants.py upgrade
    python migrations/034_add_status_to_tenants.py downgrade
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    """Add status column to tenants table."""
    print("Adding status column to tenants table...")

    async with engine.begin() as conn:
        # Add status column with default value 'draft'
        await conn.execute(text("""
                ALTER TABLE tenants
                ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'draft'
                """))

    print("✓ status column added successfully")


async def downgrade() -> None:
    """Remove status column from tenants table."""
    print("Removing status column from tenants table...")

    async with engine.begin() as conn:
        # Drop status column
        await conn.execute(text("""
                ALTER TABLE tenants
                DROP COLUMN IF EXISTS status
                """))

    print("✓ status column removed successfully")


async def main() -> None:
    """Run migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Add status column to tenants table migration")
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade"],
        help="Migration action (upgrade or downgrade)",
    )
    args = parser.parse_args()

    if args.action == "upgrade":
        await upgrade()
    elif args.action == "downgrade":
        await downgrade()

    # Close database connections
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
