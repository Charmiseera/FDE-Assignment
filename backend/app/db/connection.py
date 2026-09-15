"""
Single source of truth for building the SQLAlchemy engine URL and connect_args.

Handles:
  T1 - Session-mode pooler is the default (IPv4, supports prepared statements).
       Direct connection is supported via DB_TARGET=direct but needs IPv6 or add-on.
  T2 - asyncpg does NOT accept ?sslmode= query params. TLS is configured via
       ssl.SSLContext through connect_args, never via URL params.
  T3 - Prepared-statement safety: session mode keeps statement_cache_size at
       asyncpg default (100). Transaction mode forces statement_cache_size=0
       and adds a unique prepared_statement_name_func to avoid name collisions.

Usage:
    from app.db.connection import build_engine_kwargs
    engine = create_async_engine(**build_engine_kwargs(settings.DATABASE_URL))
"""
from __future__ import annotations

import ssl
import time
import uuid
from typing import Any
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

import structlog

from app.core.config import settings

logger = structlog.get_logger()


def _strip_sslmode(url: str) -> str:
    """
    Remove libpq-style sslmode and sslrootcert params from a URL.

    asyncpg raises at connect time if these are present, because it does not
    understand libpq query parameters. TLS is configured via connect_args.
    """
    parsed = urlparse(url)
    if not parsed.query:
        return url
    params = parse_qs(parsed.query, keep_blank_values=True)
    banned = {"sslmode", "sslrootcert", "sslcert", "sslkey"}
    stripped = {k: v for k, v in params.items() if k not in banned}
    had_banned = len(params) != len(stripped)
    if had_banned:
        logger.warning(
            "db_url_sslmode_stripped",
            removed_params=list(set(params) & banned),
            hint="TLS is configured via connect_args, not URL params. "
                 "See SUPABASE_SSL_REQUIRED and SUPABASE_CA_CERT_PATH.",
        )
    clean_query = urlencode(stripped, doseq=True)
    return urlunparse(parsed._replace(query=clean_query))


def _build_ssl_context() -> ssl.SSLContext | bool | None:
    """
    Build an SSL context for asyncpg.

    - SUPABASE_SSL_REQUIRED=true  -> require TLS
    - SUPABASE_CA_CERT_PATH set   -> verify with provided root cert
    - Default                     -> TLS enabled with check_hostname=False for pooler
    """
    if not settings.SUPABASE_SSL_REQUIRED:
        return None  # local postgres with no TLS

    ctx = ssl.create_default_context()
    ca_path = settings.SUPABASE_CA_CERT_PATH
    if ca_path:
        ctx.load_verify_locations(cafile=ca_path)
    else:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


def build_engine_kwargs(database_url: str) -> dict[str, Any]:
    """
    Build the keyword arguments for create_async_engine from a DATABASE_URL.

    Returns a dict suitable for: create_async_engine(**build_engine_kwargs(url))
    """
    # Fail fast if placeholder value was not replaced
    if "[PWD]" in database_url or "YOUR_PASSWORD" in database_url:
        raise ValueError(
            "DATABASE_URL still contains a placeholder password. "
            "Fill in the actual password from the Supabase dashboard."
        )

    clean_url = _strip_sslmode(database_url)
    ssl_ctx = _build_ssl_context()

    connect_args: dict[str, Any] = {}
    if ssl_ctx is not None:
        connect_args["ssl"] = ssl_ctx

    # search_path: ensure 'extensions' is on the path so pgvector's vector type
    # resolves without schema qualification (T4 — pgvector in extensions schema).
    connect_args["server_settings"] = {"search_path": "public,extensions"}

    pool_mode = settings.SUPABASE_POOL_MODE.lower()
    if pool_mode == "transaction":
        # Transaction mode: prepared statements are not supported across connections.
        # statement_cache_size=0 disables asyncpg's prepared statement cache.
        connect_args["statement_cache_size"] = 0
        # unique prepared_statement_name_func prevents name collisions in the
        # pool when the same statement is prepared by multiple connections.
        connect_args["prepared_statement_name_func"] = lambda: f"__asyncpg_{uuid.uuid4().hex}"
        logger.info("db_connection_mode", mode="transaction", note="prepared statements disabled")
    else:
        # Session mode (default): prepared statements work normally.
        logger.info("db_connection_mode", mode="session")

    return {
        "url": clean_url,
        "echo": settings.LOG_LEVEL.upper() == "DEBUG",
        "future": True,
        "pool_pre_ping": True,
        "pool_recycle": 300,  # 5 min — avoids stale pooler connections
        "pool_size": 5,
        "max_overflow": 5,
        "connect_args": connect_args,
    }


def build_cli_engine_kwargs(database_url: str) -> dict[str, Any]:
    """
    Build engine kwargs for the ingestion CLI (batch job, not request-path).

    Uses NullPool so connections are created and closed per-operation — avoids
    holding pooled connections open during a long-running ingest job.
    """
    from sqlalchemy.pool import NullPool
    kwargs = build_engine_kwargs(database_url)
    # Replace pool settings with NullPool
    for pool_key in ("pool_size", "max_overflow", "pool_recycle", "pool_pre_ping"):
        kwargs.pop(pool_key, None)
    kwargs["poolclass"] = NullPool
    return kwargs


def measure_db_latency_ms(engine) -> float | None:
    """
    Return measured round-trip latency (ms) for a SELECT 1 against the engine.
    Returns None if the check fails (caller decides how to handle).
    Used by the health endpoint (T9).
    """
    import asyncio
    from sqlalchemy import text

    async def _measure():
        start = time.monotonic()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return (time.monotonic() - start) * 1000

    try:
        return asyncio.get_event_loop().run_until_complete(_measure())
    except Exception:
        return None
