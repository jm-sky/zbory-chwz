"""Permission resolution for church platform ACL."""

from __future__ import annotations

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.redis import get_redis
from app.modules.auth.models import User
from app.modules.churches.acl_models import RoleDB, UserPermissionDB, UserRoleAssignmentDB
from app.modules.churches.acl_seed import Permission
from app.modules.churches.db_models import BranchDB, ChurchDB, CommunityDB, RegionDB
from app.modules.churches.permission_cache import PermissionCache, UserGrantSnapshot

Scope = tuple[str, str]


class PermissionService:
    def __init__(self, db: AsyncSession, cache: PermissionCache) -> None:
        self.db = db
        self.cache = cache

    async def resolve(self, user: User, permission: str, scope: Scope) -> bool:
        if user.isAdmin or user.isOwner:
            return True

        chain = await self.scope_chain(scope[0], scope[1])
        if not chain:
            return False

        snapshot = await self._load_snapshot(user.id)

        for scope_type, scope_id in chain:
            effect = snapshot.user_permissions.get((scope_type, scope_id, permission))
            if effect == "deny":
                return False

        for scope_type, scope_id in chain:
            effect = snapshot.user_permissions.get((scope_type, scope_id, permission))
            if effect == "allow":
                return True
            granted = snapshot.role_grants.get((scope_type, scope_id), set())
            if permission in granted:
                return True

        return False

    async def has_anywhere(self, user: User, permission: str) -> bool:
        if user.isAdmin or user.isOwner:
            return True

        snapshot = await self._load_snapshot(user.id)
        scopes: set[Scope] = set(snapshot.role_grants.keys())
        for scope_type, scope_id, _perm in snapshot.user_permissions:
            scopes.add((scope_type, scope_id))

        for scope in scopes:
            if await self.resolve(user, permission, scope):
                return True
        return False

    async def allowed_church_ids(self, user: User, permission: str) -> set[str] | None:
        if user.isAdmin or user.isOwner:
            return None

        snapshot = await self._load_snapshot(user.id)
        result = await self.db.execute(select(ChurchDB.id, ChurchDB.region_id, ChurchDB.community_id))
        allowed: set[str] = set()
        for church_id, region_id, community_id in result.all():
            chain = self._church_chain(church_id, region_id, community_id)
            if permission in self._permissions_for_chain(snapshot, chain):
                allowed.add(church_id)
        return allowed

    async def permissions_for_user(self, user: User) -> dict[str, object]:
        if user.isAdmin or user.isOwner:
            return {
                "isAdmin": user.isAdmin,
                "isOwner": user.isOwner,
                "scopes": await self._admin_scopes(),
                "churches": [],
            }

        snapshot = await self._load_snapshot(user.id)
        scope_perms: dict[Scope, set[str]] = {k: set(v) for k, v in snapshot.role_grants.items()}

        for (scope_type, scope_id, perm), effect in snapshot.user_permissions.items():
            key = (scope_type, scope_id)
            if effect == "allow":
                scope_perms.setdefault(key, set()).add(perm)
            elif effect == "deny":
                scope_perms.setdefault(key, set()).discard(perm)

        names = await self._resolve_scope_names([scope for scope, perms in scope_perms.items() if perms])
        scopes = [
            {
                "scopeType": st,
                "scopeId": sid,
                "name": names.get((st, sid), sid),
                "source": "acl",
                "permissions": sorted(perms),
            }
            for (st, sid), perms in sorted(scope_perms.items())
            if perms
        ]

        church_result = await self.db.execute(select(ChurchDB.id, ChurchDB.region_id, ChurchDB.community_id))
        churches = []
        for church_id, region_id, community_id in church_result.all():
            chain = self._church_chain(church_id, region_id, community_id)
            perms = self._permissions_for_chain(snapshot, chain)
            if perms:
                churches.append({"churchId": church_id, "permissions": sorted(perms)})

        return {
            "isAdmin": False,
            "isOwner": False,
            "scopes": scopes,
            "churches": churches,
        }

    async def _admin_scopes(self) -> list[dict[str, object]]:
        """Synthetic scopes for admin/owner: every community, region, and church.

        `churches` stays empty — `can()` short-circuits on isAdmin/isOwner. Branch
        scopes are omitted so the governance picker stays usable (G6 depth).
        """
        all_perms = sorted(p.value for p in Permission)
        scopes: list[dict[str, object]] = []

        communities = await self.db.execute(select(CommunityDB.id, CommunityDB.name).order_by(CommunityDB.name))
        for scope_id, name in communities.all():
            scopes.append(
                {
                    "scopeType": "community",
                    "scopeId": scope_id,
                    "name": name,
                    "source": "admin",
                    "permissions": all_perms,
                }
            )

        regions = await self.db.execute(select(RegionDB.id, RegionDB.name).order_by(RegionDB.name))
        for scope_id, name in regions.all():
            scopes.append(
                {
                    "scopeType": "region",
                    "scopeId": scope_id,
                    "name": name,
                    "source": "admin",
                    "permissions": all_perms,
                }
            )

        churches = await self.db.execute(select(ChurchDB.id, ChurchDB.name).order_by(ChurchDB.name))
        for scope_id, name in churches.all():
            scopes.append(
                {
                    "scopeType": "church",
                    "scopeId": scope_id,
                    "name": name,
                    "source": "admin",
                    "permissions": all_perms,
                }
            )

        return scopes

    async def _resolve_scope_names(self, scopes: list[Scope]) -> dict[Scope, str]:
        if not scopes:
            return {}

        by_type: dict[str, set[str]] = {}
        for scope_type, scope_id in scopes:
            by_type.setdefault(scope_type, set()).add(scope_id)

        names: dict[Scope, str] = {}

        if community_ids := by_type.get("community"):
            result = await self.db.execute(select(CommunityDB.id, CommunityDB.name).where(CommunityDB.id.in_(community_ids)))
            for scope_id, name in result.all():
                names[("community", scope_id)] = name

        if region_ids := by_type.get("region"):
            result = await self.db.execute(select(RegionDB.id, RegionDB.name).where(RegionDB.id.in_(region_ids)))
            for scope_id, name in result.all():
                names[("region", scope_id)] = name

        if church_ids := by_type.get("church"):
            result = await self.db.execute(select(ChurchDB.id, ChurchDB.name).where(ChurchDB.id.in_(church_ids)))
            for scope_id, name in result.all():
                names[("church", scope_id)] = name

        if branch_ids := by_type.get("branch"):
            result = await self.db.execute(select(BranchDB.id, BranchDB.name).where(BranchDB.id.in_(branch_ids)))
            for scope_id, name in result.all():
                names[("branch", scope_id)] = name

        return names

    @staticmethod
    def _church_chain(church_id: str, region_id: str | None, community_id: str) -> list[Scope]:
        chain: list[Scope] = [("church", church_id)]
        if region_id:
            chain.append(("region", region_id))
        chain.append(("community", community_id))
        return chain

    @staticmethod
    def _permissions_for_chain(snapshot: UserGrantSnapshot, chain: list[Scope]) -> set[str]:
        """Effective permissions across a scope chain: role grants and `allow` exceptions
        union, minus any permission `deny`-ed anywhere in the chain (deny is global in the
        chain, per architecture §2 — not "nearest wins")."""
        denied: set[str] = set()
        granted: set[str] = set()
        for scope in chain:
            granted |= snapshot.role_grants.get(scope, set())
            for (scope_type, scope_id, perm), effect in snapshot.user_permissions.items():
                if (scope_type, scope_id) != scope:
                    continue
                if effect == "deny":
                    denied.add(perm)
                elif effect == "allow":
                    granted.add(perm)
        return granted - denied

    async def role_permissions_in_scope(self, user: User, scope: Scope) -> set[str]:
        """Permissions the user effectively holds *at* `scope`, inherited down the same chain
        `resolve()` walks. Used by the subset rule (assert_can_grant_role, §5.1): a regional
        bishop granted at ("region", r) must be recognized as holding church-level permissions
        for churches in that region, not just grants placed exactly on ("church", church_id)."""
        if user.isAdmin or user.isOwner:
            return {p.value for p in Permission}

        snapshot = await self._load_snapshot(user.id)
        chain = await self.scope_chain(scope[0], scope[1])
        return self._permissions_for_chain(snapshot, chain)

    async def scope_chain(self, scope_type: str, scope_id: str) -> list[Scope]:
        if scope_type == "branch":
            branch = await self.db.get(BranchDB, scope_id)
            if not branch:
                return []
            return [("branch", branch.id), *await self.scope_chain("church", branch.church_id)]

        if scope_type == "church":
            church = await self.db.get(ChurchDB, scope_id)
            if not church:
                return []
            chain: list[Scope] = [("church", church.id)]
            if church.region_id:
                chain.append(("region", church.region_id))
            chain.append(("community", church.community_id))
            return chain

        if scope_type == "region":
            region = await self.db.get(RegionDB, scope_id)
            if not region:
                return []
            return [("region", region.id), ("community", region.community_id)]

        if scope_type == "community":
            community = await self.db.get(CommunityDB, scope_id)
            if not community:
                return []
            return [("community", scope_id)]

        return []

    async def _load_snapshot(self, user_id: str) -> UserGrantSnapshot:
        cached = await self.cache.get_user_snapshot(user_id)
        if cached is not None:
            return cached

        role_result = await self.db.execute(
            select(UserRoleAssignmentDB)
            .where(UserRoleAssignmentDB.user_id == user_id)
            .options(
                selectinload(UserRoleAssignmentDB.role).selectinload(RoleDB.permissions),
            )
        )
        assignments = list(role_result.scalars().all())

        role_grants: dict[Scope, set[str]] = {}
        for assignment in assignments:
            role = assignment.role
            if not role:
                continue
            scope = (assignment.scope_type, assignment.scope_id)
            role_grants.setdefault(scope, set()).update(rp.permission for rp in role.permissions)

        perm_result = await self.db.execute(select(UserPermissionDB).where(UserPermissionDB.user_id == user_id))
        user_permissions: dict[tuple[str, str, str], str] = {}
        for row in perm_result.scalars().all():
            user_permissions[(row.scope_type, row.scope_id, row.permission)] = row.effect

        snapshot = UserGrantSnapshot(role_grants=role_grants, user_permissions=user_permissions)
        await self.cache.set_user_snapshot(user_id, snapshot)
        return snapshot


def _build_cache(redis: Redis | None) -> PermissionCache:
    return PermissionCache(redis)


async def get_permission_cache(redis: Redis = Depends(get_redis)) -> PermissionCache:
    return _build_cache(redis)


def get_permission_service(
    db: AsyncSession = Depends(get_db),
    cache: PermissionCache = Depends(get_permission_cache),
) -> PermissionService:
    return PermissionService(db, cache)
