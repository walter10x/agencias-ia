"""Token bucket rate limiter using Redis."""

from __future__ import annotations

import redis.asyncio as async_redis


class RateLimiter:
    """Token bucket rate limiter using Redis.

    Limits messages per WhatsApp phone number within a sliding window.
    """

    def __init__(
        self,
        redis_client: async_redis.Redis,
        max_tokens: int = 10,
        window_seconds: int = 60,
    ) -> None:
        self._redis = redis_client
        self._max_tokens = max_tokens
        self._window_seconds = window_seconds

    async def check(self, phone: str) -> bool:
        """Check if phone is within rate limit. Returns True if allowed."""
        key = f"rate_limit:{phone}"
        current = await self._redis.get(key)

        if current is None:
            await self._redis.setex(key, self._window_seconds, 1)
            return True

        count = int(current)
        if count >= self._max_tokens:
            return False

        await self._redis.incr(key)
        return True
