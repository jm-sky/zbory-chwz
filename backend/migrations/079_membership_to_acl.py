"""Migration: backfill owner/admin memberships to pastor ACL grants.

Usage:
    python migrations/079_membership_to_acl.py upgrade
    python migrations/079_membership_to_acl.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import delete, select

from app.common.id_utils import generate_id
from app.core.database import AsyncSessionLocal
from app.modules.auth.db_models import UserDB  # noqa: F401 — register users for FK resolution
from app.modules.churches.acl_models import RoleDB, UserRoleAssignmentDB
from app.modules.churches.db_models import ChurchDB
from app.modules.tenants.db_models import TenantMembershipDB


async def upgrade() -> None:
    print("Backfilling pastor ACL grants from tenant memberships...")
    created = 0

    async with AsyncSessionLocal() as db:
        role_result = await db.execute(select(RoleDB).where(RoleDB.name == "pastor"))
        pastor_role = role_result.scalar_one_or_none()
        if not pastor_role:
            print("Pastor role missing — run ACL seed first")
            return

        stmt = select(TenantMembershipDB).join(ChurchDB, ChurchDB.id == TenantMembershipDB.tenant_id).where(TenantMembershipDB.role.in_(("owner", "admin")))
        memberships = (await db.execute(stmt)).scalars().all()

        for membership in memberships:
            existing = await db.execute(
                select(UserRoleAssignmentDB).where(
                    UserRoleAssignmentDB.user_id == membership.user_id,
                    UserRoleAssignmentDB.role_id == pastor_role.id,
                    UserRoleAssignmentDB.scope_type == "church",
                    UserRoleAssignmentDB.scope_id == membership.tenant_id,
                )
            )
            if existing.scalar_one_or_none():
                continue
            db.add(
                UserRoleAssignmentDB(
                    id=generate_id(),
                    user_id=membership.user_id,
                    role_id=pastor_role.id,
                    scope_type="church",
                    scope_id=membership.tenant_id,
                    source_assignment_id=None,
                )
            )
            created += 1

        await db.commit()

    print(f"Migration 079 upgrade complete. Created {created} grants.")


async def downgrade() -> None:
    print("Removing pastor ACL grants without source_assignment_id...")

    async with AsyncSessionLocal() as db:
        role_result = await db.execute(select(RoleDB).where(RoleDB.name == "pastor"))
        pastor_role = role_result.scalar_one_or_none()
        if not pastor_role:
            return
        await db.execute(
            delete(UserRoleAssignmentDB).where(
                UserRoleAssignmentDB.role_id == pastor_role.id,
                UserRoleAssignmentDB.source_assignment_id.is_(None),
                UserRoleAssignmentDB.scope_type == "church",
            )
        )
        await db.commit()

    print("Migration 079 downgrade complete.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
