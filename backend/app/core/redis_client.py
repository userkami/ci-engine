"""Shared async Redis client (Pub/Sub bridge between worker and API).

The client is process-scoped and lazily created. Connection failures are
logged; every call site wraps its operations so a Redis outage degrades
behaviour (skipped progress events / DB-polling fallback for SSE) instead
of failing the research job.
"""

from __future__ import annotations

import logging
from typing import Optional

from redis.asyncio import Redis, from_url
from redis.exceptions import RedisError

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """Return the process-wide Redis client, creating it on first use."""
    global _client
    if _client is None:
        _client = from_url(
            get_settings().redis_url,
            decode_responses=True,
            socket_connect_timeout=5.0,
            socket_timeout=5.0,
            health_check_interval=30,
        )
        # Probe eagerly so a broker outage surfaces early and loudly.
        try:
            await _client.ping()
        except (RedisError, OSError) as exc:
            logger.warning(
                "Redis unavailable at %s: %s", get_settings().redis_url, exc
            )
    return _client


async def close_redis() -> None:
    """Release the shared client; call on application shutdown."""
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:
            logger.exception("error closing Redis client")
        _client = None