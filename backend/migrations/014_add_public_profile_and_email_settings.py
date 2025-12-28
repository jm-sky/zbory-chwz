"""Migration: Add public profile and email settings.

This migration adds the following fields:
- user_settings: is_public_profile (boolean, default False)
- user_settings: is_public_email (boolean, default False)

Usage:
    python migrations/014_add_public_profile_and_email_settings.py upgrade
    python migrations/014_add_public_profile_and_email_settings.py downgrade
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine


async def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists in the database."""
    result = await conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = :table_name
            );
        """
        ),
        {"table_name": table_name},
    )
    return result.scalar() is True


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
    """Add public profile and email settings."""
    print("Adding public profile and email settings...")

    async with engine.begin() as conn:
        # Add is_public_profile and is_public_email to user_settings
        settings_exist = await table_exists(conn, "user_settings")
        if settings_exist:
            # Add is_public_profile
            is_public_profile_exists = await column_exists(
                conn, "user_settings", "is_public_profile"
            )
            if not is_public_profile_exists:
                print("Adding is_public_profile column to user_settings...")
                await conn.execute(
                    text(
                        """
                        ALTER TABLE user_settings 
                        ADD COLUMN is_public_profile BOOLEAN DEFAULT FALSE NOT NULL;
                    """
                    )
                )
                print("✓ Added is_public_profile column to user_settings")
            else:
                print("✓ is_public_profile column already exists in user_settings")

            # Add is_public_email
            is_public_email_exists = await column_exists(
                conn, "user_settings", "is_public_email"
            )
            if not is_public_email_exists:
                print("Adding is_public_email column to user_settings...")
                await conn.execute(
                    text(
                        """
                        ALTER TABLE user_settings 
                        ADD COLUMN is_public_email BOOLEAN DEFAULT FALSE NOT NULL;
                    """
                    )
                )
                print("✓ Added is_public_email column to user_settings")
            else:
                print("✓ is_public_email column already exists in user_settings")
        else:
            print("user_settings table does not exist, skipping...")

    print("✓ Migration completed successfully")


async def downgrade() -> None:
    """Remove public profile and email settings."""
    print("Removing public profile and email settings...")

    async with engine.begin() as conn:
        # Remove is_public_profile and is_public_email from user_settings
        settings_exist = await table_exists(conn, "user_settings")
        if settings_exist:
            # Remove is_public_profile
            is_public_profile_exists = await column_exists(
                conn, "user_settings", "is_public_profile"
            )
            if is_public_profile_exists:
                await conn.execute(
                    text(
                        """
                        ALTER TABLE user_settings 
                        DROP COLUMN IF EXISTS is_public_profile;
                    """
                    )
                )
                print("✓ Removed is_public_profile column from user_settings")
            else:
                print("✓ is_public_profile column does not exist in user_settings")

            # Remove is_public_email
            is_public_email_exists = await column_exists(
                conn, "user_settings", "is_public_email"
            )
            if is_public_email_exists:
                await conn.execute(
                    text(
                        """
                        ALTER TABLE user_settings 
                        DROP COLUMN IF EXISTS is_public_email;
                    """
                    )
                )
                print("✓ Removed is_public_email column from user_settings")
            else:
                print("✓ is_public_email column does not exist in user_settings")

    print("✓ Migration downgrade completed successfully")


async def main() -> None:
    """Run migration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Add public profile and email settings migration"
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
