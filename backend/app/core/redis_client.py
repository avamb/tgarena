"""
Redis Client Module

Provides async Redis connection and caching utilities for the application.
"""

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

try:
    from app.core.config import settings
except ModuleNotFoundError:
    from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client
_redis_client: Optional[Redis] = None


async def get_redis_client() -> Redis:
    """
    Get or create the Redis client connection.

    Returns:
        Redis: The async Redis client instance.
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info(f"Redis client connected to {settings.REDIS_URL}")

    return _redis_client


async def close_redis_client():
    """Close the Redis client connection."""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client connection closed")


async def ping_redis() -> bool:
    """
    Check if Redis is reachable.

    Returns:
        bool: True if Redis responds to PING, False otherwise.
    """
    try:
        client = await get_redis_client()
        result = await client.ping()
        return result
    except Exception as e:
        logger.error(f"Redis ping failed: {e}")
        return False


class CacheService:
    """
    Service for caching data in Redis with JSON serialization.
    """

    def __init__(self, prefix: str = "cache"):
        """
        Initialize the cache service.

        Args:
            prefix: Key prefix for all cache entries.
        """
        self.prefix = prefix

    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: The cache key.

        Returns:
            The cached value or None if not found.
        """
        try:
            client = await get_redis_client()
            value = await client.get(self._make_key(key))

            if value is not None:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)

            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set a value in cache.

        Args:
            key: The cache key.
            value: The value to cache (must be JSON serializable).
            ttl: Time to live in seconds (optional).

        Returns:
            True if successful, False otherwise.
        """
        try:
            client = await get_redis_client()
            serialized = json.dumps(value)

            if ttl:
                await client.setex(self._make_key(key), ttl, serialized)
            else:
                await client.set(self._make_key(key), serialized)

            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a value from cache.

        Args:
            key: The cache key.

        Returns:
            True if successful, False otherwise.
        """
        try:
            client = await get_redis_client()
            await client.delete(self._make_key(key))
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: The pattern to match (e.g., "events:*").

        Returns:
            Number of keys deleted.
        """
        try:
            client = await get_redis_client()
            full_pattern = self._make_key(pattern)
            keys = []

            async for key in client.scan_iter(match=full_pattern):
                keys.append(key)

            if keys:
                deleted = await client.delete(*keys)
                logger.debug(f"Cache DELETE PATTERN: {pattern} ({deleted} keys)")
                return deleted

            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: The cache key.

        Returns:
            True if key exists, False otherwise.
        """
        try:
            client = await get_redis_client()
            return await client.exists(self._make_key(key)) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def get_ttl(self, key: str) -> int:
        """
        Get the TTL of a key in seconds.

        Args:
            key: The cache key.

        Returns:
            TTL in seconds, -1 if no TTL, -2 if key doesn't exist.
        """
        try:
            client = await get_redis_client()
            return await client.ttl(self._make_key(key))
        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return -2


# Default cache service instances
event_cache = CacheService(prefix="events")
session_cache = CacheService(prefix="sessions")
general_cache = CacheService(prefix="app")
