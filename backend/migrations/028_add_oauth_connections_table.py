"""Migration: Add oauth_connections table.

This migration adds the oauth_connections table to support multiple OAuth providers
per user account. This allows users to link multiple OAuth providers (Google, Facebook, etc.)
to a single account.

Usage:
    python migrations/028_add_oauth_connections_table.py upgrade
    python migrations/028_add_oauth_connections_table.py downgrade
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


async def upgrade() -> None:
    """Add oauth_connections table."""
    print("Adding oauth_connections table...")

    async with engine.begin() as conn:
        connections_exist = await table_exists(conn, "oauth_connections")
        if not connections_exist:
            print("Creating oauth_connections table...")
            await conn.execute(
                text(
                    """
                    CREATE TABLE oauth_connections (
                        id VARCHAR(36) PRIMARY KEY,
                        user_id VARCHAR(36) NOT NULL,
                        provider VARCHAR(50) NOT NULL,
                        provider_id VARCHAR(255) NOT NULL,
                        email VARCHAR(255),
                        name VARCHAR(255),
                        avatar_url TEXT,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
                        CONSTRAINT fk_oauth_connections_user
                            FOREIGN KEY (user_id)
                            REFERENCES users(id)
                            ON DELETE CASCADE,
                        CONSTRAINT uq_oauth_connections_provider
                            UNIQUE (provider, provider_id)
                    );
                """
                )
            )
            # Create indexes for better query performance
            await conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_oauth_connections_user_id
                    ON oauth_connections(user_id);
                """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_oauth_connections_provider
                    ON oauth_connections(provider, provider_id);
                """
                )
            )
            print("✓ Created oauth_connections table")
        else:
            print("✓ oauth_connections table already exists")


async def downgrade() -> None:
    """Remove oauth_connections table."""
    print("Removing oauth_connections table...")

    async with engine.begin() as conn:
        connections_exist = await table_exists(conn, "oauth_connections")
        if connections_exist:
            print("Dropping oauth_connections table...")
            await conn.execute(
                text(
                    """
                    DROP TABLE IF EXISTS oauth_connections CASCADE;
                """
                )
            )
            print("✓ Dropped oauth_connections table")
        else:
            print("✓ oauth_connections table does not exist")


async def main() -> None:
    """Run migration based on command line argument."""
    if len(sys.argv) < 2:
        print(
            "Usage: python migrations/028_add_oauth_connections_table.py [upgrade|downgrade]"
        )
        sys.exit(1)

    command = sys.argv[1].lower()
    if command == "upgrade":
        await upgrade()
    elif command == "downgrade":
        await downgrade()
    else:
        print(f"Unknown command: {command}")
        print(
            "Usage: python migrations/028_add_oauth_connections_table.py [upgrade|downgrade]"
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
