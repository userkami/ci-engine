"""Redis Pub/Sub progress publishing for research jobs.

Messages are published to ``job_progress:{job_id}`` (SPEC.md §6). The
publisher is best-effort by design: if Redis is down the event is logged
and skipped — the database remains the source of truth, and the SSE
endpoint falls back to polling it.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from redis.exceptions import RedisError

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

_MAX_PUBLISH_ATTEMPTS = 3


class ProgressPublisher:
    """Publishes ``{step, message, msg, data}`` events to a job channel."""

    def __init__(self, job_id: str) -> None:
        if not job_id:
            raise ValueError("job_id is required")
        self.job_id = job_id
        self.channel = f"job_progress:{job_id}"

    async def publish(self, step: str, message: str, data: Any = None) -> None:
        """Publish one progress event; retries briefly, then drops it.

        Never raises: progress events are advisory. The worker persists
        real state (job status + battlecard) in PostgreSQL.
        """
        payload = {
            "step": step,
            "message": message,
            "msg": message,  # alias used by BUILD_GUIDE Phase 4 payloads
            "data": data,
        }
        for attempt in range(1, _MAX_PUBLISH_ATTEMPTS + 1):
            try:
                client = await get_redis()
                await client.publish(
                    self.channel, json.dumps(payload, default=str)
                )
                return
            except (RedisError, OSError) as exc:
                if attempt == _MAX_PUBLISH_ATTEMPTS:
                    logger.warning(
                        "Redis unavailable; dropped progress event %r on %s (%s)",
                        step,
                        self.channel,
                        exc,
                    )
                else:
                    await asyncio.sleep(0.5 * attempt)