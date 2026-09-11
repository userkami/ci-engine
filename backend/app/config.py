"""Application configuration loaded from environment variables.

Every runtime setting is read once and cached; the docker-compose stack
passes values through ``env_file: .env`` (see ``.env.example``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

# Fallback used only for local development tooling (e.g. Alembic offline
# mode). Never used in production, where DATABASE_URL is always set.
DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://ci_admin:replace_with_strong_password@postgres:5432/ci_database"
)

_TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable snapshot of application configuration."""

    database_url: str
    redis_url: str = "redis://redis:6379/0"
    cors_origins: str = "http://localhost:3000"
    sql_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in _TRUE_VALUES


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide configuration (cached after first call)."""
    return Settings(
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
        cors_origins=os.getenv(
            "CORS_ORIGINS", "http://localhost:3000"
        ),
        sql_echo=_env_bool("SQL_ECHO", False),
        db_pool_size=_env_int("DB_POOL_SIZE", 5),
        db_max_overflow=_env_int("DB_MAX_OVERFLOW", 10),
    )