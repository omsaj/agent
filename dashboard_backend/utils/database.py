from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Awaitable, Callable

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from ..config.settings import get_settings
from ..models.threat_models import Base

_settings = get_settings()

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Create (or return existing) async SQLAlchemy engine."""

    global _engine
    if _engine is None:
        use_null_pool = "sqlite" in _settings.database_url
        _engine = create_async_engine(
            _settings.database_url,
            echo=False,
            future=True,
            pool_pre_ping=True,
            poolclass=NullPool if use_null_pool else None,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the global async session factory."""

    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), expire_on_commit=False, autoflush=False, autocommit=False
        )
    return _session_factory


@asynccontextmanager
async def lifespan_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()


async def get_session() -> AsyncIterator[AsyncSession]:
    async with lifespan_session() as session:
        yield session


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def shutdown() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    global _session_factory
    _session_factory = None


async def run_in_session(func: Callable[[AsyncSession], Awaitable[None]]) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await func(session)
