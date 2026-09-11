"""Runtime configuration service — database-backed overrides for env vars.

The admin UI persists configuration changes here. Values stored in the
``runtime_config`` table take precedence over environment variables and are
read at call time, so changes take effect immediately without restart.
"""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import select

from app.database import AsyncSessionFactory
from app.models import RuntimeConfig

#: Keys that this service manages. Each maps to an env var fallback.
MANAGED_KEYS = (
    "LLM_FAST_MODEL",
    "LLM_HEAVY_MODEL",
    "OPENROUTER_API_KEY",
    "TAVILY_API_KEY",
    "FIRECRAWL_API_KEY",
)


async def get_config(key: str, env_fallback: str | None = None) -> str | None:
    """Return the effective value for a config key.

    Checks the database first (admin override), then falls back to the
    environment variable, then to ``env_fallback``.
    """
    async with AsyncSessionFactory() as session:
        row = await session.get(RuntimeConfig, key)
    if row is not None and row.value:
        return row.value
    env_value = os.getenv(key, "").strip() or None
    return env_value if env_value is not None else env_fallback


async def set_config(key: str, value: str) -> None:
    """Persist a config override to the database (upsert)."""
    async with AsyncSessionFactory() as session:
        row = await session.get(RuntimeConfig, key)
        if row is None:
            row = RuntimeConfig(key=key, value=value)
            session.add(row)
        else:
            row.value = value
        await session.commit()


async def delete_config(key: str) -> bool:
    """Remove a config override (reverts to env var). Returns True if deleted."""
    async with AsyncSessionFactory() as session:
        row = await session.get(RuntimeConfig, key)
        if row is None:
            return False
        await session.delete(row)
        await session.commit()
        return True


async def list_config() -> dict[str, dict]:
    """Return all managed config keys with their effective values and sources."""
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(RuntimeConfig.key, RuntimeConfig.value)
        )
        db_overrides = {key: value for key, value in result.all()}

    entries = {}
    for key in MANAGED_KEYS:
        db_value = db_overrides.get(key)
        env_value = os.getenv(key, "").strip()
        if db_value:
            entries[key] = {"value": db_value, "source": "database"}
        elif env_value:
            entries[key] = {"value": env_value, "source": "environment"}
        else:
            entries[key] = {"value": "", "source": "none"}
    return entries
