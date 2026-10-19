"""Per-tenant / per-IP rate limiting (noisy-neighbor protection).

Uses Redis when REDIS_URL is configured (shared across replicas); otherwise a
process-local sliding window. Redis outages fail open, by design, and are
logged at warning level by the middleware.
"""

import contextlib
import time
from collections import defaultdict, deque

from app.core.config import settings


class InMemoryLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int, window: float = 60.0) -> float | None:
        now = time.monotonic()
        bucket = self._hits[key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= limit:
            return max(0.1, window - (now - bucket[0]))
        bucket.append(now)
        return None


class RateLimiter:
    def __init__(self) -> None:
        self._memory = InMemoryLimiter()
        self._redis = None

    async def start(self) -> None:
        if not settings.redis_url:
            return
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
            await client.ping()
            self._redis = client
        except Exception:
            self._redis = None

    async def stop(self) -> None:
        if self._redis is not None:
            with contextlib.suppress(Exception):
                await self._redis.aclose()
            self._redis = None

    async def hit(self, key: str, limit: int, window: int = 60) -> float | None:
        if limit <= 0:
            return None
        if self._redis is not None:
            try:
                pipe = self._redis.pipeline()
                pipe.incr(key)
                pipe.ttl(key)
                count, ttl = await pipe.execute()
                if ttl is not None and ttl < 0:
                    await self._redis.expire(key, window)
                if int(count) > limit:
                    return float(ttl) if ttl and ttl > 0 else float(window)
                return None
            except Exception:
                return self._memory.hit(key, limit, window)
        return self._memory.hit(key, limit, window)


limiter = RateLimiter()
