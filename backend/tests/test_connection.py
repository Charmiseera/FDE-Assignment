"""
Unit tests for the connection URL builder (app/db/connection.py).

All tests run without a live database.
"""
import ssl
import pytest
from unittest.mock import patch, MagicMock


# ── sslmode stripping (T2) ────────────────────────────────────────────────────

def test_strip_sslmode_from_url():
    """sslmode query param is removed from asyncpg URLs."""
    from app.db.connection import _strip_sslmode
    url = "postgresql+asyncpg://user:pw@host:5432/db?sslmode=require"
    result = _strip_sslmode(url)
    assert "sslmode" not in result
    assert "user:pw@host" in result


def test_strip_multiple_libpq_params():
    """All banned libpq params are stripped."""
    from app.db.connection import _strip_sslmode
    url = "postgresql+asyncpg://u:p@h:5432/db?sslmode=verify-full&sslrootcert=/tmp/cert.pem"
    result = _strip_sslmode(url)
    assert "sslmode" not in result
    assert "sslrootcert" not in result


def test_clean_url_unchanged():
    """URL without sslmode is returned unchanged."""
    from app.db.connection import _strip_sslmode
    url = "postgresql+asyncpg://u:p@h:5432/db"
    assert _strip_sslmode(url) == url


# ── password placeholder guard ────────────────────────────────────────────────

def test_build_engine_kwargs_rejects_placeholder_password():
    """ValueError is raised if DATABASE_URL still has [PWD] placeholder."""
    from app.db.connection import build_engine_kwargs
    with pytest.raises(ValueError, match="placeholder password"):
        build_engine_kwargs("postgresql+asyncpg://user:[PWD]@host:5432/db")


def test_build_engine_kwargs_rejects_your_password():
    """ValueError is raised if DATABASE_URL still has YOUR_PASSWORD placeholder."""
    from app.db.connection import build_engine_kwargs
    with pytest.raises(ValueError, match="placeholder password"):
        build_engine_kwargs("postgresql+asyncpg://user:YOUR_PASSWORD@host:5432/db")


# ── session mode (default) ────────────────────────────────────────────────────

def test_build_engine_kwargs_session_mode_defaults():
    """Session mode produces connect_args with ssl=None for local and no stmt cache override."""
    from app.db.connection import build_engine_kwargs
    from app.core.config import settings

    original_ssl = settings.SUPABASE_SSL_REQUIRED
    original_mode = settings.SUPABASE_POOL_MODE
    try:
        settings.SUPABASE_SSL_REQUIRED = False
        settings.SUPABASE_POOL_MODE = "session"
        kwargs = build_engine_kwargs("postgresql+asyncpg://u:pw@localhost:5432/db")
        assert kwargs["pool_size"] == 5
        assert kwargs["max_overflow"] == 5
        assert kwargs["pool_recycle"] == 300
        assert kwargs["pool_pre_ping"] is True
        # statement_cache_size NOT set in session mode
        connect_args = kwargs["connect_args"]
        assert "statement_cache_size" not in connect_args
        assert connect_args["server_settings"]["search_path"] == "public,extensions"
    finally:
        settings.SUPABASE_SSL_REQUIRED = original_ssl
        settings.SUPABASE_POOL_MODE = original_mode


# ── transaction mode (T3) ─────────────────────────────────────────────────────

def test_build_engine_kwargs_transaction_mode_disables_prepared_statements():
    """Transaction mode sets statement_cache_size=0 and prepared_statement_name_func."""
    from app.db.connection import build_engine_kwargs
    from app.core.config import settings

    original_ssl = settings.SUPABASE_SSL_REQUIRED
    original_mode = settings.SUPABASE_POOL_MODE
    try:
        settings.SUPABASE_SSL_REQUIRED = False
        settings.SUPABASE_POOL_MODE = "transaction"
        kwargs = build_engine_kwargs("postgresql+asyncpg://u:pw@localhost:5432/db")
        connect_args = kwargs["connect_args"]
        assert connect_args["statement_cache_size"] == 0
        assert "prepared_statement_name_func" in connect_args
        # Verify the func generates unique names
        f = connect_args["prepared_statement_name_func"]
        assert f() != f()
    finally:
        settings.SUPABASE_SSL_REQUIRED = original_ssl
        settings.SUPABASE_POOL_MODE = original_mode


# ── TLS context (T2) ─────────────────────────────────────────────────────────

def test_build_ssl_context_required_uses_ssl():
    """SUPABASE_SSL_REQUIRED=True produces an ssl.SSLContext in connect_args."""
    from app.db.connection import build_engine_kwargs
    from app.core.config import settings

    original = settings.SUPABASE_SSL_REQUIRED
    original_mode = settings.SUPABASE_POOL_MODE
    try:
        settings.SUPABASE_SSL_REQUIRED = True
        settings.SUPABASE_POOL_MODE = "session"
        kwargs = build_engine_kwargs("postgresql+asyncpg://u:pw@localhost:5432/db")
        assert isinstance(kwargs["connect_args"]["ssl"], ssl.SSLContext)
    finally:
        settings.SUPABASE_SSL_REQUIRED = original
        settings.SUPABASE_POOL_MODE = original_mode


# ── CLI engine (NullPool) ─────────────────────────────────────────────────────

def test_build_cli_engine_kwargs_uses_nullpool():
    """CLI engine kwargs use NullPool and drop request-path pool settings."""
    from app.db.connection import build_cli_engine_kwargs
    from sqlalchemy.pool import NullPool
    from app.core.config import settings

    original = settings.SUPABASE_SSL_REQUIRED
    original_mode = settings.SUPABASE_POOL_MODE
    try:
        settings.SUPABASE_SSL_REQUIRED = False
        settings.SUPABASE_POOL_MODE = "session"
        kwargs = build_cli_engine_kwargs("postgresql+asyncpg://u:pw@localhost:5432/db")
        assert kwargs["poolclass"] is NullPool
        assert "pool_size" not in kwargs
        assert "max_overflow" not in kwargs
    finally:
        settings.SUPABASE_SSL_REQUIRED = original
        settings.SUPABASE_POOL_MODE = original_mode
