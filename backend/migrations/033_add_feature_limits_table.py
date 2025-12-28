"""Migration: Add feature_limits table.

This migration creates a table for storing feature limits (AI and storage)
for different user roles. Limits can be configured per role and can be
overridden for specific users.

Usage:
    python migrations/033_add_feature_limits_table.py upgrade
    python migrations/033_add_feature_limits_table.py downgrade
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine


async def table_exists(conn, table_name: str) -> bool:
    """Check if a table exists in the database (PostgreSQL compatible)."""
    result = await conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = :table_name
            );
        """
        ),
        {"table_name": table_name},
    )
    return result.scalar() is True


async def upgrade() -> None:
    """Create feature_limits table."""
    print("Creating feature_limits table...")

    async with engine.begin() as conn:
        # Check if table already exists
        if await table_exists(conn, "feature_limits"):
            print("feature_limits table already exists, skipping migration...")
            return

        # Create feature_limits table
        print("Creating feature_limits table...")
        await conn.execute(
            text(
                """
                CREATE TABLE feature_limits (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    role VARCHAR(50) NOT NULL UNIQUE,
                    ai_limit NUMERIC(10,2) NULL,
                    storage_limit_bytes BIGINT NOT NULL,
                    description TEXT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    CONSTRAINT valid_role CHECK (role IN ('user', 'premium', 'admin', 'owner'))
                )
            """
            )
        )
        await conn.execute(
            text("CREATE INDEX idx_feature_limits_role ON feature_limits(role)")
        )
        print("✓ Created feature_limits table")

        # Insert default limits
        print("Inserting default limits...")
        await conn.execute(
            text(
                """
                INSERT INTO feature_limits (role, ai_limit, storage_limit_bytes, description)
                VALUES
                    ('user', 0.00, 20971520, 'Regular user: no AI access without own token, 20MB storage'),
                    ('premium', 5.00, 52428800, 'Premium user: $5 AI limit, 50MB storage'),
                    ('admin', NULL, 209715200, 'Admin: unlimited AI, 200MB storage'),
                    ('owner', NULL, 1073741824, 'Owner: unlimited AI, 1GB storage')
                ON CONFLICT (role) DO NOTHING
            """
            )
        )
        print("✓ Inserted default limits")

    print("✓ Migration completed successfully")


async def downgrade() -> None:
    """Drop feature_limits table."""
    print("Dropping feature_limits table...")

    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS feature_limits CASCADE"))
        print("✓ Dropped feature_limits table")

    print("✓ Downgrade completed successfully")


async def main() -> None:
    """Run migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Add feature_limits table migration")
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
