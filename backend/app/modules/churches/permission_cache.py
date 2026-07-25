"""Redis-backed cache for ACL user grant snapshots."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

ACL_EPOCH_KEY = "acl:epoch"
ACL_USER_KEY_PREFIX = "acl:v"
DEFAULT_TTL_SECONDS = 300

Scope = tuple[str, str]


@dataclass(frozen=True)
class UserGrantSnapshot:
    role_grants: dict[Scope, set[str]]
    user_permissions: dict[tuple[str, str, str], str]

    def to_json(self) -> str:
        payload = {
            "role_grants": [
                {
                    "scope_type": st,
                    "scope_id": sid,
                    "permissions": sorted(perms),
                }
                for (st, sid), perms in self.role_grants.items()
            ],
            "user_permissions": [
                {
                    "scope_type": st,
                    "scope_id": sid,
                    "permission": perm,
                    "effect": effect,
                }
                for (st, sid, perm), effect in self.user_permissions.items()
            ],
        }
        return json.dumps(payload)

    @classmethod
    def from_json(cls, raw: str) -> UserGrantSnapshot:
        data = json.loads(raw)
        role_grants: dict[Scope, set[str]] = {}
        for item in data.get("role_grants", []):
            role_grants[(item["scope_type"], item["scope_id"])] = set(item.get("permissions", []))
        user_permissions: dict[tuple[str, str, str], str] = {}
        for item in data.get("user_permissions", []):
            user_permissions[(item["scope_type"], item["scope_id"], item["permission"])] = item["effect"]
        return cls(role_grants=role_grants, user_permissions=user_permissions)


class PermissionCache:
    def __init__(self, redis: Redis | None) -> None:
        self._redis = redis

    async def get_epoch(self) -> int:
        if not self._redis:
            return 0
        try:
            raw = await self._redis.get(ACL_EPOCH_KEY)
            return int(raw) if raw is not None else 0
        except Exception as exc:
            logger.warning("ACL cache epoch read failed: %s", exc)
            return 0

    async def bump_epoch(self) -> None:
        if not self._redis:
            return
        try:
            await self._redis.incr(ACL_EPOCH_KEY)
        except Exception as exc:
            logger.warning("ACL cache epoch bump failed: %s", exc)

    async def get_user_snapshot(self, user_id: str) -> UserGrantSnapshot | None:
        if not self._redis:
            return None
        try:
            epoch = await self.get_epoch()
            key = f"{ACL_USER_KEY_PREFIX}{epoch}:{user_id}"
            raw = await self._redis.get(key)
            if raw is None:
                return None
            return UserGrantSnapshot.from_json(raw)
        except Exception as exc:
            logger.warning("ACL cache read failed for user %s: %s", user_id, exc)
            return None

    async def set_user_snapshot(self, user_id: str, snapshot: UserGrantSnapshot) -> None:
        if not self._redis:
            return
        try:
            epoch = await self.get_epoch()
            key = f"{ACL_USER_KEY_PREFIX}{epoch}:{user_id}"
            await self._redis.set(key, snapshot.to_json(), ex=DEFAULT_TTL_SECONDS)
        except Exception as exc:
            logger.warning("ACL cache write failed for user %s: %s", user_id, exc)

    async def invalidate_user(self, user_id: str) -> None:
        if not self._redis:
            return
        try:
            epoch = await self.get_epoch()
            key = f"{ACL_USER_KEY_PREFIX}{epoch}:{user_id}"
            await self._redis.delete(key)
        except Exception as exc:
            logger.warning("ACL cache invalidate failed for user %s: %s", user_id, exc)
