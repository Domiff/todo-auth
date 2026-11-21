from collections.abc import Awaitable, Callable
from datetime import timedelta
from functools import lru_cache
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
    TimeoutError as RedisTimeoutError,
)

from backend.core.logging import get_logger
from backend.core.settings import settings

logger = get_logger(__name__)


class RedisClient:
    def __init__(self, redis) -> None:
        self.redis: Redis = redis

    async def _do(
        self, func: Callable[..., Awaitable[Any] | Any], *args, **kwargs
    ) -> Any:
        operation = getattr(func, "__name__", repr(func))
        try:
            return await func(*args, **kwargs)
        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.error(
                "Redis connection error",
                extra={"operation": operation, "error": str(e)},
            )
            raise
        except Exception as e:
            logger.error(
                "Redis operation failed",
                extra={"operation": operation, "error": str(e)},
            )
            raise

    async def set(
        self,
        key: str,
        value,
        expire: int | timedelta = settings.redis.EXPIRE,
        nx: bool = False,
    ) -> bool:
        result = await self._do(self.redis.set, key, value, ex=expire, nx=nx)
        logger.info("redis_set", extra={"redis_key": key, "written": bool(result)})
        return bool(result)

    async def get(self, key: str) -> str | None:
        value = await self._do(self.redis.get, key)
        if value is None:
            logger.info("redis_get_miss", extra={"redis_key": key})
            return None
        logger.info("redis_get", extra={"redis_key": key})
        return value

    async def exists(self, key: str) -> int:
        logger.info("redis_exists", extra={"redis_key": key})
        return await self._do(self.redis.exists, key)

    async def delete(self, key: str) -> None:
        await self._do(self.redis.delete, key)
        logger.info("redis_delete", extra={"redis_key": key})


def key_builder(prefix: str, key: str | int) -> str:
    return f"{prefix}:{key}"


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(
        settings.redis.url,
        max_connections=settings.redis.CONNECTION_POOL_MAXSIZE,
        decode_responses=True,
    )


redis = RedisClient(get_redis())
