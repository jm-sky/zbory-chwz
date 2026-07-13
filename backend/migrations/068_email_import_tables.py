"""Migration: Inbound clergy e-mail import tables + last-updated tracking.

Adds `email_import_messages` (IMAP-polled inbox queue) and
`congregation_change_log` (full change history, admin/pastor/bishop-visible),
plus `last_updated_at`/`last_updated_label` on `congregation_addresses` for a
quick "who last touched this" badge without joining the full log.

See docs/plans/2026-07-13--clergy-email-updates.md.

Usage:
    python migrations/068_email_import_tables.py upgrade
    python migrations/068_email_import_tables.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Creating email import tables...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS email_import_messages (
                    id VARCHAR(36) PRIMARY KEY,
                    message_id VARCHAR(500),
                    raw_from VARCHAR(500) NOT NULL,
                    sender_person_id VARCHAR(36) REFERENCES persons(id) ON DELETE SET NULL,
                    resolved_tenant_id VARCHAR(36) REFERENCES tenants(id) ON DELETE SET NULL,
                    resolution VARCHAR(32) NOT NULL,
                    auth_spf VARCHAR(16),
                    auth_dkim VARCHAR(16),
                    auth_dmarc VARCHAR(16),
                    extraction_json TEXT,
                    verification_score DOUBLE PRECISION,
                    verification_reasoning TEXT,
                    status VARCHAR(16) NOT NULL DEFAULT 'pending',
                    reviewed_by_user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
                    reviewed_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """))
        await conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ux_email_import_messages_message_id
                ON email_import_messages (message_id)
                WHERE message_id IS NOT NULL
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_email_import_messages_status
                ON email_import_messages (status)
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_email_import_messages_resolved_tenant_id
                ON email_import_messages (resolved_tenant_id)
                """))

        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS congregation_change_log (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    section VARCHAR(16) NOT NULL,
                    field VARCHAR(64) NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    source VARCHAR(32) NOT NULL,
                    actor_label VARCHAR(255) NOT NULL,
                    actor_user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
                    actor_person_id VARCHAR(36) REFERENCES persons(id) ON DELETE SET NULL,
                    email_import_message_id VARCHAR(36) REFERENCES email_import_messages(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_congregation_change_log_tenant_id_created_at
                ON congregation_change_log (tenant_id, created_at DESC)
                """))

        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                ADD COLUMN IF NOT EXISTS last_updated_at TIMESTAMPTZ
                """))
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                ADD COLUMN IF NOT EXISTS last_updated_label VARCHAR(255)
                """))

    print("Migration 068 upgrade complete.")


async def downgrade() -> None:
    print("Dropping email import tables...")

    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE congregation_addresses DROP COLUMN IF EXISTS last_updated_label"))
        await conn.execute(text("ALTER TABLE congregation_addresses DROP COLUMN IF EXISTS last_updated_at"))
        await conn.execute(text("DROP TABLE IF EXISTS congregation_change_log"))
        await conn.execute(text("DROP TABLE IF EXISTS email_import_messages"))

    print("Migration 068 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
