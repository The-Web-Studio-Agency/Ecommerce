"""Async database engine and session factory.

Transaction ownership:
    * the request dependency (`get_db`) opens, rolls back and closes the session;
    * the SERVICE layer decides when to commit (it owns the business transaction);
    * repositories never commit.

Pool sizing is explicit rather than left to the SQLAlchemy defaults, because the
effective connection count is (pool_size + max_overflow) x worker processes and
must stay below the server's `max_connections`.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_settings = get_settings()

engine: AsyncEngine = create_async_engine(
    _settings.database_url,
    echo=_settings.db_echo,
    pool_pre_ping=True,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
    # Recycle below any proxy/database idle timeout so long-lived workers do not
    # hand out connections the server has already closed.
    pool_recycle=_settings.db_pool_recycle_seconds,
    # Fail fast when the pool is saturated instead of queueing without bound.
    pool_timeout=_settings.db_pool_timeout_seconds,
    connect_args={
        # Server-side cap: Postgres aborts the statement itself, so a runaway
        # query cannot hold a pooled connection open indefinitely.
        "server_settings": {
            "statement_timeout": str(_settings.db_statement_timeout_seconds * 1000),
            "application_name": _settings.app_name,
        },
    },
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    # Keep attributes loaded after commit so response serialisation does not
    # trigger a surprise refresh (or fail on a closed session).
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a request-scoped session.

    Rolls back and closes on the way out; committing is the service layer's job.
    """
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def dispose_engine() -> None:
    """Close all pooled connections (application shutdown)."""
    await engine.dispose()
