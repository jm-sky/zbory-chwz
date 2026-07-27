"""Migration: invite token columns on users, for the governance invite flow (G1).

Deliberately separate from reset_token/reset_token_expiry: sharing one pair of columns
would mean a "forgot password" request from an already-invited user silently cancels their
invite (and vice versa) — a quiet failure mode that is hard to diagnose. The two flows share
infrastructure (token encoding, EmailService, set-password page), not storage.

Usage:
    python migrations/081_user_invitations.py upgrade
    python migrations/081_user_invitations.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Adding invite columns to users table...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS invite_token TEXT
                """))
        await conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS invite_token_expiry TIMESTAMPTZ
                """))
        await conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS invited_at TIMESTAMPTZ
                """))
        await conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS invited_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL
                """))

    print("Migration 081 upgrade complete.")


async def downgrade() -> None:
    print("Dropping invite columns from users table...")

    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS invited_by"))
        await conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS invited_at"))
        await conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS invite_token_expiry"))
        await conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS invite_token"))

    print("Migration 081 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
