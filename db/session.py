"""
Database session management.
Vercel serverless: each invocation gets its own connection.
Local: persistent connection pool.
"""
import os
import logging
from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine
)
from .models import Base
from config import config

logger = logging.getLogger(__name__)

# Vercel serverless functions are stateless — each cold start recreates the engine.
# We use NullPool for serverless to avoid connection leaks across invocations.
def _make_engine() -> AsyncEngine:
    db_url = config.DATABASE_URL
    is_serverless = config.is_vercel

    kwargs: dict = {"echo": False, "pool_pre_ping": True}

    if is_serverless:
        # NullPool: no persistent connections — safe for serverless
        from sqlalchemy.pool import NullPool
        kwargs["poolclass"] = NullPool
        logger.info("DB engine: NullPool (serverless mode)")
    else:
        # Local: small pool
        kwargs.update({"pool_size": 5, "max_overflow": 10})
        logger.info("DB engine: connection pool (local mode)")

    return create_async_engine(db_url, **kwargs)


# Module-level engine — recreated per cold start on Vercel, persistent locally
_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


def get_session_factory() -> async_sessionmaker:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


# Convenient alias used by middlewares
AsyncSessionLocal = get_session_factory()


async def init_db():
    """Create all tables if they don't exist. Called once on startup."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified/created")


async def close_db():
    """Dispose engine — call on shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("DB engine disposed")
