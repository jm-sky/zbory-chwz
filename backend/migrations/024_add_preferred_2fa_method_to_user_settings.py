"""Migration: Add preferred 2FA method to user settings.

This migration adds the following field:
- user_settings: preferred_2fa_method (string, nullable, default NULL)

Usage:
    python migrations/024_add_preferred_2fa_method_to_user_settings.py upgrade
    python migrations/024_add_preferred_2fa_method_to_user_settings.py downgrade
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine


async def column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    result = await conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = :table_name
                AND column_name = :column_name
            );
        """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar() is True


async def upgrade() -> None:
    """Add preferred 2FA method to user settings."""
    print("Adding preferred_2fa_method field to user_settings table...")

    async with engine.begin() as conn:
        if not await column_exists(conn, "user_settings", "preferred_2fa_method"):
            await conn.execute(
                text(
                    """
                    ALTER TABLE user_settings
                    ADD COLUMN preferred_2fa_method VARCHAR(20) NULL;
                """
                )
            )
            print("✓ Added preferred_2fa_method field to user_settings table")
        else:
            print("preferred_2fa_method column already exists, skipping migration...")

    print("✓ Migration completed successfully")


async def downgrade() -> None:
    """Remove preferred 2FA method from user settings."""
    print("Removing preferred_2fa_method field from user_settings table...")

    async with engine.begin() as conn:
        if await column_exists(conn, "user_settings", "preferred_2fa_method"):
            await conn.execute(
                text(
                    """
                    ALTER TABLE user_settings
                    DROP COLUMN preferred_2fa_method;
                """
                )
            )
            print("✓ Removed preferred_2fa_method field from user_settings table")
        else:
            print("preferred_2fa_method column does not exist, skipping downgrade...")

    print("✓ Downgrade completed successfully")


async def main() -> None:
    """Run migration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Add preferred 2FA method to user settings migration"
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
