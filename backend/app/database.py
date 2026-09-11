"""Async database engine, session factory and declarative base.

Reads ``DATABASE_URL`` from the environment via :mod:`app.config`.
The URL may use the ``postgres://`` or ``postgresql://`` scheme — it is
normalised to the asyncpg dialect variant automatically.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

_settings = get_settings()


def _normalise_postgres_url(url: str) -> str:
    """Return a URL SQLAlchemy can resolve to the asyncpg driver."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    raise ValueError(
        "DATABASE_URL must start with 'postgresql+asyncpg://', "
        "'postgresql://' or 'postgres://'"
    )


engine = create_async_engine(
    _normalise_postgres_url(_settings.database_url),
    echo=_settings.sql_echo,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
    pool_pre_ping=True,
)

#: Request-scoped factory; ``expire_on_commit=False`` keeps attribute
#: access cheap and avoids implicit IO after commit in async handlers.
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model in :mod:`app.models`."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped async session.

    The transaction is committed/rolled back by the caller; the session is
    always closed and returned to the pool on exit.
    """
    async with AsyncSessionFactory() as session:
        yield session


async def dispose_engine() -> None:
    """Release pooled connections. Call on application shutdown."""
    await engine.dispose()