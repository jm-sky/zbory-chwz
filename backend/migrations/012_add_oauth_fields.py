"""Migration: Add OAuth fields to users table.

This migration adds OAuth authentication fields to the users table:
- oauth_provider: Provider name (google, github, etc.)
- oauth_provider_id: Provider's unique user ID
- avatar_url: User's profile picture URL
- Makes hashed_password nullable for OAuth-only users

Usage:
    python migrations/011_add_oauth_fields.py upgrade
    python migrations/011_add_oauth_fields.py downgrade
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
    """Add OAuth fields to users table."""
    print("Adding OAuth fields to users table...")

    async with engine.begin() as conn:
        # Add oauth_provider column
        if not await column_exists(conn, "users", "oauth_provider"):
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(50)")
            )
            print("  ✓ Added oauth_provider column")
        else:
            print("  ⊙ oauth_provider column already exists, skipping")

        # Add oauth_provider_id column
        if not await column_exists(conn, "users", "oauth_provider_id"):
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN oauth_provider_id VARCHAR(255)")
            )
            print("  ✓ Added oauth_provider_id column")
        else:
            print("  ⊙ oauth_provider_id column already exists, skipping")

        # Add avatar_url column
        if not await column_exists(conn, "users", "avatar_url"):
            await conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url TEXT"))
            print("  ✓ Added avatar_url column")
        else:
            print("  ⊙ avatar_url column already exists, skipping")

        # Make hashed_password nullable (for OAuth users)
        # SQLite doesn't support ALTER COLUMN, so we need to check the dialect
        dialect = conn.dialect.name
        if dialect == "sqlite":
            print("  Note: SQLite detected - hashed_password will remain NOT NULL")
            print("  OAuth users will use a placeholder hash value")
        elif dialect == "postgresql":
            await conn.execute(
                text("ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL")
            )
            print("  ✓ Made hashed_password nullable")

        # Create index for OAuth lookups
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_users_oauth "
                "ON users(oauth_provider, oauth_provider_id)"
            )
        )

    print("✓ OAuth fields added successfully")


async def downgrade() -> None:
    """Remove OAuth fields from users table."""
    print("Removing OAuth fields from users table...")

    async with engine.begin() as conn:
        # Drop index
        await conn.execute(text("DROP INDEX IF EXISTS idx_users_oauth"))

        # Drop columns
        dialect = conn.dialect.name
        if dialect == "sqlite":
            # SQLite doesn't support DROP COLUMN easily
            print(
                "  Warning: SQLite doesn't support DROP COLUMN. Manual intervention required."
            )
            print("  You may need to recreate the table to remove these columns.")
        else:
            await conn.execute(text("ALTER TABLE users DROP COLUMN avatar_url"))
            await conn.execute(text("ALTER TABLE users DROP COLUMN oauth_provider_id"))
            await conn.execute(text("ALTER TABLE users DROP COLUMN oauth_provider"))

            # Make hashed_password NOT NULL again (for PostgreSQL)
            if dialect == "postgresql":
                await conn.execute(
                    text("ALTER TABLE users ALTER COLUMN hashed_password SET NOT NULL")
                )

    print("✓ OAuth fields removed successfully")


async def main() -> None:
    """Run migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Add OAuth fields migration")
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
