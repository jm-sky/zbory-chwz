"""Migration: Add Owner and Premium role fields to users table.

This migration adds is_owner and is_premium boolean fields to the users table
to support the new role system.

Usage:
    python migrations/025_add_owner_and_premium_roles.py upgrade
    python migrations/025_add_owner_and_premium_roles.py downgrade
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text


async def upgrade() -> None:
    """Add is_owner and is_premium columns to users table."""
    print("Adding is_owner and is_premium columns to users table...")

    async with engine.begin() as conn:
        # Add is_owner column
        await conn.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS is_owner BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
        )

        # Add is_premium column
        await conn.execute(
            text(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS is_premium BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
        )

    print("✓ is_owner and is_premium columns added successfully")


async def downgrade() -> None:
    """Remove is_owner and is_premium columns from users table."""
    print("Removing is_owner and is_premium columns from users table...")

    async with engine.begin() as conn:
        # Drop is_owner column
        await conn.execute(
            text(
                """
                ALTER TABLE users
                DROP COLUMN IF EXISTS is_owner
                """
            )
        )

        # Drop is_premium column
        await conn.execute(
            text(
                """
                ALTER TABLE users
                DROP COLUMN IF EXISTS is_premium
                """
            )
        )

    print("✓ is_owner and is_premium columns removed successfully")


async def main() -> None:
    """Run migration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Add Owner and Premium roles migration"
    )
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
