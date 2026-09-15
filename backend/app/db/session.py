"""
Database engine and session factory.

The request-path engine is built once at module load with a modest connection
pool (pool_size=5, max_overflow=5, pool_recycle=300s). These settings are
appropriate for a persistent long-running container against a hosted pooler.

The ingestion CLI must call make_cli_engine() to get a NullPool engine — it
should NOT import AsyncSessionLocal directly, because the request-path pool
holds idle connections for the lifetime of the container, which is wasteful
for a batch job.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.db.connection import build_engine_kwargs, build_cli_engine_kwargs


# ── Request-path engine ───────────────────────────────────────────────────────
engine = create_async_engine(**build_engine_kwargs(settings.DATABASE_URL))

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ── CLI engine factory ────────────────────────────────────────────────────────
def make_cli_engine():
    """
    Create a short-lived NullPool engine for the ingestion CLI.

    Call this instead of importing AsyncSessionLocal, so the batch job does
    not hold a persistent pool open during a long-running ingest.

    Usage:
        cli_engine = make_cli_engine()
        CLISession = async_sessionmaker(bind=cli_engine, ...)
        async with CLISession() as session:
            ...
        await cli_engine.dispose()
    """
    return create_async_engine(**build_cli_engine_kwargs(settings.DATABASE_URL))
