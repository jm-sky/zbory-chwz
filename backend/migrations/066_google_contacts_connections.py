"""Migration: Add google_contacts_connections table.

Persists per-user Google Contacts (People API) OAuth connections, separate
from `oauth_connections` (login identity linking, no tokens). See
docs/plans/2026-07-10--google-contacts-sync.md.

Usage:
    python migrations/066_google_contacts_connections.py upgrade
    python migrations/066_google_contacts_connections.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def table_exists(conn, table_name: str) -> bool:
    result = await conn.execute(
        text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = :table_name
            );
        """),
        {"table_name": table_name},
    )
    return result.scalar() is True


async def upgrade() -> None:
    print("Adding google_contacts_connections table...")

    async with engine.begin() as conn:
        if await table_exists(conn, "google_contacts_connections"):
            print("✓ google_contacts_connections table already exists")
            return

        await conn.execute(text("""
                CREATE TABLE google_contacts_connections (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    scope VARCHAR(32) NOT NULL DEFAULT 'readonly',
                    access_token TEXT NOT NULL,
                    refresh_token TEXT,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    connected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
                    revoked_at TIMESTAMP WITH TIME ZONE,
                    CONSTRAINT fk_google_contacts_connections_user
                        FOREIGN KEY (user_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE,
                    CONSTRAINT uq_google_contacts_connections_user
                        UNIQUE (user_id)
                );
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_google_contacts_connections_user_id
                ON google_contacts_connections(user_id);
                """))
        print("✓ Created google_contacts_connections table")


async def downgrade() -> None:
    print("Removing google_contacts_connections table...")

    async with engine.begin() as conn:
        if not await table_exists(conn, "google_contacts_connections"):
            print("✓ google_contacts_connections table does not exist")
            return

        await conn.execute(text("DROP TABLE IF EXISTS google_contacts_connections CASCADE;"))
        print("✓ Dropped google_contacts_connections table")


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python migrations/066_google_contacts_connections.py [upgrade|downgrade]")
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
