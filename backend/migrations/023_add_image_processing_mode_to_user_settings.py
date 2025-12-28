"""Migration: Add image processing mode to user settings.

This migration adds the following field:
- user_settings: image_processing_mode (string, nullable, default 'balanced')

Usage:
    python migrations/023_add_image_processing_mode_to_user_settings.py upgrade
    python migrations/023_add_image_processing_mode_to_user_settings.py downgrade
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
    """Add image processing mode to user settings."""
    print("Adding image_processing_mode field to user_settings table...")

    async with engine.begin() as conn:
        if not await column_exists(conn, "user_settings", "image_processing_mode"):
            await conn.execute(
                text(
                    """
                    ALTER TABLE user_settings
                    ADD COLUMN image_processing_mode VARCHAR(20) NULL DEFAULT 'balanced';
                """
                )
            )
            print("✓ Added image_processing_mode field to user_settings table")
        else:
            print("image_processing_mode column already exists, skipping migration...")

    print("✓ Migration completed successfully")


async def downgrade() -> None:
    """Remove image processing mode from user settings."""
    print("Removing image_processing_mode field from user_settings table...")

    async with engine.begin() as conn:
        if await column_exists(conn, "user_settings", "image_processing_mode"):
            await conn.execute(
                text(
                    """
                    ALTER TABLE user_settings
                    DROP COLUMN image_processing_mode;
                """
                )
            )
            print("✓ Removed image_processing_mode field from user_settings table")
        else:
            print("image_processing_mode column does not exist, skipping downgrade...")

    print("✓ Downgrade completed successfully")


async def main() -> None:
    """Run migration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Add image processing mode to user settings migration"
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
