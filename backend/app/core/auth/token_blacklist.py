"""Token blacklist service using Redis.

This service manages revoked JWT tokens to prevent their reuse
after logout or account deletion.
"""

import hashlib
import logging
from datetime import UTC, datetime

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class TokenBlacklistService:
    """Service for managing blacklisted JWT tokens."""

    def __init__(self, redis_client: Redis, key_prefix: str = "blacklist:token:"):
        """Initialize token blacklist service.

        Args:
            redis_client: Async Redis client
            key_prefix: Prefix for Redis keys (default: "blacklist:token:")
        """
        self.redis = redis_client
        self.key_prefix = key_prefix

    def _get_token_hash(self, token: str) -> str:
        """Generate SHA-256 hash of token for storage.

        Args:
            token: JWT token string

        Returns:
            Hex-encoded SHA-256 hash
        """
        return hashlib.sha256(token.encode()).hexdigest()

    def _get_redis_key(self, token: str) -> str:
        """Generate Redis key for token.

        Args:
            token: JWT token string

        Returns:
            Redis key string
        """
        token_hash = self._get_token_hash(token)
        return f"{self.key_prefix}{token_hash}"

    async def blacklist_token(
        self, token: str, expires_at: int, reason: str = "logout"
    ) -> None:
        """Add token to blacklist.

        Args:
            token: JWT token to blacklist
            expires_at: Unix timestamp when token expires
            reason: Reason for blacklisting (e.g., "logout", "account_deleted")

        Note:
            Token is stored until its natural expiration (TTL = exp - now).
            After expiration, Redis automatically removes it.
        """
        now = int(datetime.now(UTC).timestamp())
        ttl = expires_at - now

        if ttl <= 0:
            # Token already expired, no need to blacklist
            logger.debug("Token already expired, skipping blacklist")
            return

        key = self._get_redis_key(token)
        value = f"{reason}:{now}"

        await self.redis.setex(key, ttl, value)
        logger.info(f"Token blacklisted: reason={reason}, ttl={ttl}s")

    async def is_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted.

        Args:
            token: JWT token to check

        Returns:
            True if token is blacklisted, False otherwise
        """
        key = self._get_redis_key(token)
        exists = await self.redis.exists(key)
        return bool(exists)

    async def blacklist_all_user_tokens(
        self, user_id: str, reason: str = "account_deleted"
    ) -> int:
        """Blacklist all tokens for a user.

        Note:
            This is a placeholder. In production, you'd need to:
            1. Store user_id → token mapping in Redis
            2. Or use a different token storage strategy

        Args:
            user_id: User ID
            reason: Reason for blacklisting

        Returns:
            Number of tokens blacklisted
        """
        # TODO: Implement user token tracking
        # For now, this is handled by individual token blacklisting
        logger.warning(
            f"blacklist_all_user_tokens called for user_id={user_id}, but user token tracking not implemented"
        )
        return 0

    async def get_blacklist_stats(self) -> dict:
        """Get statistics about blacklisted tokens.

        Returns:
            Dict with blacklist statistics
        """
        pattern = f"{self.key_prefix}*"
        cursor = 0
        count = 0

        # Scan Redis keys (non-blocking)
        while True:
            cursor, keys = await self.redis.scan(
                cursor=cursor, match=pattern, count=100
            )
            count += len(keys)

            if cursor == 0:
                break

        return {
            "total_blacklisted": count,
            "key_prefix": self.key_prefix,
        }
