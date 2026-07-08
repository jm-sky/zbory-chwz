"""Migration: Add token_version column to users table.

This migration adds the token_version column used for token revocation.
Incrementing this value invalidates all previously issued tokens for a user,
serving as a fallback mechanism when Redis is unavailable.

Usage:
    python migrations/055_add_token_version_to_users.py upgrade
    python migrations/055_add_token_version_to_users.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine


async def column_exists(conn, table_name: str, column_name: str) -> bool:
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
    print("Adding token_version column to users table...")

    async with engine.begin() as conn:
        if await column_exists(conn, "users", "token_version"):
            print("✓ Column token_version already exists, skipping...")
            return

        await conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0;"
            )
        )
        print("✓ Added token_version column to users table")


async def downgrade() -> None:
    print("Removing token_version column from users table...")

    async with engine.begin() as conn:
        if not await column_exists(conn, "users", "token_version"):
            print("✓ Column token_version does not exist, skipping...")
            return

        await conn.execute(text("ALTER TABLE users DROP COLUMN token_version;"))
        print("✓ Removed token_version column from users table")


async def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python migrations/055_add_token_version_to_users.py [upgrade|downgrade]"
        )
        sys.exit(1)

    command = sys.argv[1].lower()
    if command == "upgrade":
        await upgrade()
    elif command == "downgrade":
        await downgrade()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
