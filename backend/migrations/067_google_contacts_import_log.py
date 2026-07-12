"""Migration: Add google_contacts_import_log table.

Audit trail for Google Contacts import decisions (Phase 3). See
docs/plans/2026-07-10--google-contacts-sync.md.

Usage:
    python migrations/067_google_contacts_import_log.py upgrade
    python migrations/067_google_contacts_import_log.py downgrade
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
    print("Adding google_contacts_import_log table...")

    async with engine.begin() as conn:
        if await table_exists(conn, "google_contacts_import_log"):
            print("✓ google_contacts_import_log table already exists")
            return

        await conn.execute(text("""
                CREATE TABLE google_contacts_import_log (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    google_resource_name VARCHAR(255) NOT NULL,
                    entity_type VARCHAR(16) NOT NULL,
                    matched_entity_id VARCHAR(36),
                    action VARCHAR(16) NOT NULL,
                    imported_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
                    CONSTRAINT fk_google_contacts_import_log_user
                        FOREIGN KEY (user_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE
                );
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_google_contacts_import_log_user_id
                ON google_contacts_import_log(user_id);
                """))
        print("✓ Created google_contacts_import_log table")


async def downgrade() -> None:
    print("Removing google_contacts_import_log table...")

    async with engine.begin() as conn:
        if not await table_exists(conn, "google_contacts_import_log"):
            print("✓ google_contacts_import_log table does not exist")
            return

        await conn.execute(text("DROP TABLE IF EXISTS google_contacts_import_log CASCADE;"))
        print("✓ Dropped google_contacts_import_log table")


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python migrations/067_google_contacts_import_log.py [upgrade|downgrade]")
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
