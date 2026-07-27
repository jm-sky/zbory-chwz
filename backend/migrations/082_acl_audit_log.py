"""Migration: acl_audit_log table — append-only audit trail for ACL-affecting actions
(role grants/revokes, permission exceptions, invites, cascading assignment revocations).

Usage:
    python migrations/082_acl_audit_log.py upgrade
    python migrations/082_acl_audit_log.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    print("Creating acl_audit_log table...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS acl_audit_log (
                    id VARCHAR(36) PRIMARY KEY,
                    batch_id VARCHAR(36) NOT NULL,
                    actor_user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
                    actor_label TEXT NOT NULL,
                    target_user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
                    target_label TEXT NOT NULL,
                    action VARCHAR(32) NOT NULL,
                    scope_type VARCHAR(32),
                    scope_id VARCHAR(36),
                    role_name VARCHAR(64),
                    permission VARCHAR(64),
                    effect VARCHAR(8),
                    old_value TEXT,
                    new_value TEXT,
                    source VARCHAR(32) NOT NULL DEFAULT 'ui',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_acl_audit_log_scope
                ON acl_audit_log (scope_type, scope_id, created_at DESC)
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_acl_audit_log_target_user_id
                ON acl_audit_log (target_user_id, created_at DESC)
                """))

    print("Migration 082 upgrade complete.")


async def downgrade() -> None:
    print("Dropping acl_audit_log table...")

    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS acl_audit_log"))

    print("Migration 082 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
