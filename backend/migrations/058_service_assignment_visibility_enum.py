"""Migration: Replace boolean visibility flags with visibility enum columns.

Usage:
    python migrations/058_service_assignment_visibility_enum.py upgrade
    python migrations/058_service_assignment_visibility_enum.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Migrating service_assignments visibility to enum columns...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD COLUMN IF NOT EXISTS card_visibility VARCHAR(32)
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD COLUMN IF NOT EXISTS phone_visibility VARCHAR(32)
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD COLUMN IF NOT EXISTS email_visibility VARCHAR(32)
                """))

        await conn.execute(text("""
                UPDATE service_assignments
                SET card_visibility = CASE
                    WHEN show_on_card THEN 'public'
                    ELSE 'hidden'
                END
                WHERE card_visibility IS NULL
                  AND EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'service_assignments'
                      AND column_name = 'show_on_card'
                  )
                """))
        await conn.execute(text("""
                UPDATE service_assignments
                SET phone_visibility = CASE
                    WHEN phone_public THEN 'public'
                    ELSE 'hidden'
                END
                WHERE phone_visibility IS NULL
                  AND EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'service_assignments'
                      AND column_name = 'phone_public'
                  )
                """))
        await conn.execute(text("""
                UPDATE service_assignments
                SET email_visibility = CASE
                    WHEN email_public THEN 'public'
                    ELSE 'hidden'
                END
                WHERE email_visibility IS NULL
                  AND EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'service_assignments'
                      AND column_name = 'email_public'
                  )
                """))

        await conn.execute(text("""
                UPDATE service_assignments
                SET card_visibility = 'public'
                WHERE card_visibility IS NULL
                """))
        await conn.execute(text("""
                UPDATE service_assignments
                SET phone_visibility = 'public'
                WHERE phone_visibility IS NULL
                """))
        await conn.execute(text("""
                UPDATE service_assignments
                SET email_visibility = 'authenticated'
                WHERE email_visibility IS NULL
                """))

        await conn.execute(text("""
                ALTER TABLE service_assignments
                ALTER COLUMN card_visibility SET NOT NULL,
                ALTER COLUMN card_visibility SET DEFAULT 'public'
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ALTER COLUMN phone_visibility SET NOT NULL,
                ALTER COLUMN phone_visibility SET DEFAULT 'public'
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ALTER COLUMN email_visibility SET NOT NULL,
                ALTER COLUMN email_visibility SET DEFAULT 'authenticated'
                """))

        await conn.execute(text("""
                ALTER TABLE service_assignments
                DROP CONSTRAINT IF EXISTS ck_service_assignments_card_visibility
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD CONSTRAINT ck_service_assignments_card_visibility
                CHECK (card_visibility IN ('hidden', 'public', 'authenticated', 'pastors'))
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                DROP CONSTRAINT IF EXISTS ck_service_assignments_phone_visibility
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD CONSTRAINT ck_service_assignments_phone_visibility
                CHECK (phone_visibility IN ('hidden', 'public', 'authenticated', 'pastors'))
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                DROP CONSTRAINT IF EXISTS ck_service_assignments_email_visibility
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD CONSTRAINT ck_service_assignments_email_visibility
                CHECK (email_visibility IN ('hidden', 'public', 'authenticated', 'pastors'))
                """))

        await conn.execute(text("ALTER TABLE service_assignments DROP COLUMN IF EXISTS show_on_card"))
        await conn.execute(text("ALTER TABLE service_assignments DROP COLUMN IF EXISTS phone_public"))
        await conn.execute(text("ALTER TABLE service_assignments DROP COLUMN IF EXISTS email_public"))

    print("Migration 058 upgrade complete.")


async def downgrade() -> None:
    print("Reverting service_assignments visibility to boolean columns...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD COLUMN IF NOT EXISTS show_on_card BOOLEAN NOT NULL DEFAULT TRUE
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD COLUMN IF NOT EXISTS phone_public BOOLEAN NOT NULL DEFAULT TRUE
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD COLUMN IF NOT EXISTS email_public BOOLEAN NOT NULL DEFAULT FALSE
                """))

        await conn.execute(text("""
                UPDATE service_assignments
                SET show_on_card = card_visibility != 'hidden'
                """))
        await conn.execute(text("""
                UPDATE service_assignments
                SET phone_public = phone_visibility != 'hidden'
                """))
        await conn.execute(text("""
                UPDATE service_assignments
                SET email_public = email_visibility = 'public'
                """))

        await conn.execute(text("ALTER TABLE service_assignments DROP CONSTRAINT IF EXISTS ck_service_assignments_email_visibility"))
        await conn.execute(text("ALTER TABLE service_assignments DROP CONSTRAINT IF EXISTS ck_service_assignments_phone_visibility"))
        await conn.execute(text("ALTER TABLE service_assignments DROP CONSTRAINT IF EXISTS ck_service_assignments_card_visibility"))
        await conn.execute(text("ALTER TABLE service_assignments DROP COLUMN IF EXISTS email_visibility"))
        await conn.execute(text("ALTER TABLE service_assignments DROP COLUMN IF EXISTS phone_visibility"))
        await conn.execute(text("ALTER TABLE service_assignments DROP COLUMN IF EXISTS card_visibility"))

    print("Migration 058 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
