"""Migration: drop legacy congregation_contact_persons table.

Migrates any remaining rows to persons + service_assignments, then drops
source_contact_person_id and congregation_contact_persons.

Usage:
    python migrations/066_drop_congregation_contact_persons.py upgrade
    python migrations/066_drop_congregation_contact_persons.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.common.id_utils import generate_id
from app.core.database import AsyncSessionLocal, engine
from app.modules.churches.contact_sync import (
    load_service_types_by_slug,
    resolve_service_type_for_title,
    split_person_name,
)
from app.modules.churches.db_models import PersonDB, ServiceAssignmentDB


async def _migrate_remaining_contact_persons(session) -> int:
    table_exists = await session.scalar(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'congregation_contact_persons'
            )
            """))
    if not table_exists:
        return 0

    result = await session.execute(text("""
            SELECT id, tenant_id, church_id, name, title, email, phone, "order"
            FROM congregation_contact_persons
            """))
    rows = result.fetchall()
    if not rows:
        return 0

    service_types_by_slug = await load_service_types_by_slug(session)
    migrated = 0

    for row in rows:
        cp_id, tenant_id, church_id, name, title, email, phone, order = row
        church_id = church_id or tenant_id

        if await _has_source_migration(session, cp_id):
            continue

        first_name, last_name = split_person_name(name)
        service_type_id, custom_name = resolve_service_type_for_title(
            title,
            service_types_by_slug,
        )

        person = PersonDB(
            id=generate_id(),
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
        )
        session.add(person)
        await session.flush()

        session.add(
            ServiceAssignmentDB(
                id=generate_id(),
                person_id=person.id,
                service_type_id=service_type_id,
                custom_service_name=custom_name,
                description=None,
                scope_type="church",
                scope_id=church_id,
                show_on_list=True,
                profile_visibility="public",
                phone_visibility="public" if phone else "hidden",
                email_visibility="public" if email else "hidden",
                sort_order=order,
            )
        )
        migrated += 1

    await session.flush()
    return migrated


async def _has_source_migration(session, contact_person_id: str) -> bool:
    column_exists = await session.scalar(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'service_assignments'
                  AND column_name = 'source_contact_person_id'
            )
            """))
    if not column_exists:
        return False

    existing = await session.scalar(
        text("""
            SELECT 1 FROM service_assignments
            WHERE source_contact_person_id = :contact_person_id
            LIMIT 1
            """),
        {"contact_person_id": contact_person_id},
    )
    return existing is not None


async def upgrade() -> None:
    print("Migrating remaining contact persons and dropping legacy table...")

    async with AsyncSessionLocal() as session:
        migrated = await _migrate_remaining_contact_persons(session)
        await session.commit()
        print(f"Migrated {migrated} legacy contact person(s) to service assignments")

    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE service_assignments DROP COLUMN IF EXISTS source_contact_person_id"))
        await conn.execute(text("DROP TABLE IF EXISTS congregation_contact_persons"))

    print("Migration 066 upgrade complete")


async def downgrade() -> None:
    print("Recreating congregation_contact_persons (data not restored)...")

    async with engine.begin() as conn:
        await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS congregation_contact_persons (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(36) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    church_id VARCHAR(36) REFERENCES churches(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    title VARCHAR(100),
                    email VARCHAR(255),
                    phone VARCHAR(50),
                    "order" INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """))
        await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_congregation_contact_persons_tenant_id
                ON congregation_contact_persons(tenant_id)
                """))
        await conn.execute(text("""
                ALTER TABLE service_assignments
                ADD COLUMN IF NOT EXISTS source_contact_person_id VARCHAR(36) NULL
                """))

    print("Migration 066 downgrade complete (empty legacy table only)")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
