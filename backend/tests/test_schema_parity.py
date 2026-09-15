import os
import pytest
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

SUPABASE_TEST_URL = os.environ.get("SUPABASE_TEST_URL", "")
requires_db = pytest.mark.skipif(
    not SUPABASE_TEST_URL,
    reason="SUPABASE_TEST_URL not set -- skipping live schema parity test",
)


@requires_db
def test_all_expected_tables_exist():
    """All four ORM tables must exist in the live schema."""
    engine = sa.create_engine(SUPABASE_TEST_URL)
    inspector = sa_inspect(engine)
    live = set(inspector.get_table_names(schema="public"))
    missing = {"sessions", "messages", "artifacts", "chunks"} - live
    assert not missing, f"Tables missing from live schema: {missing}"
    engine.dispose()


@requires_db
def test_chunks_columns_match_orm():
    """All ORM Chunk columns must exist in the live DB."""
    from app.db.models import Chunk  # noqa: PLC0415
    engine = sa.create_engine(SUPABASE_TEST_URL)
    inspector = sa_inspect(engine)
    live = {c["name"] for c in inspector.get_columns("chunks", schema="public")}
    orm = {c.name for c in Chunk.__table__.columns}
    missing = orm - live
    assert not missing, f"ORM columns not in live DB: {missing}"
    extra = live - orm
    if extra:
        print(f"  INFO: extra columns in DB not in ORM: {extra}")
    engine.dispose()


@requires_db
def test_embedding_model_column_nullable():
    """embedding_model must exist on chunks and be nullable."""
    engine = sa.create_engine(SUPABASE_TEST_URL)
    inspector = sa_inspect(engine)
    cols = {c["name"]: c for c in inspector.get_columns("chunks", schema="public")}
    assert "embedding_model" in cols, "embedding_model column missing from chunks"
    assert cols["embedding_model"]["nullable"] is True, "embedding_model must be nullable"
    engine.dispose()


@requires_db
def test_sessions_columns_match_orm():
    """All ORM Session columns must exist in the live DB."""
    from app.db.models import Session  # noqa: PLC0415
    engine = sa.create_engine(SUPABASE_TEST_URL)
    inspector = sa_inspect(engine)
    live = {c["name"] for c in inspector.get_columns("sessions", schema="public")}
    orm = {c.name for c in Session.__table__.columns}
    missing = orm - live
    assert not missing, f"Session ORM columns not in live DB: {missing}"
    engine.dispose()


@requires_db
def test_rls_enabled_on_all_tables():
    """RLS must be enabled on all four tables."""
    engine = sa.create_engine(SUPABASE_TEST_URL)
    q = sa.text(
        "SELECT relname, relrowsecurity FROM pg_class"
        " WHERE relname IN ('sessions','messages','artifacts','chunks')"
        " AND relkind = 'r'"
    )
    with engine.connect() as conn:
        rows = {r.relname: r.relrowsecurity for r in conn.execute(q)}
    for table in ("sessions", "messages", "artifacts", "chunks"):
        assert table in rows, f"{table} not in pg_class"
        assert rows[table] is True, f"RLS not enabled on {table}"
    engine.dispose()


@requires_db
def test_hnsw_index_exists_on_chunks():
    """HNSW cosine index with vector_cosine_ops must exist on chunks."""
    engine = sa.create_engine(SUPABASE_TEST_URL)
    q = sa.text(
        "SELECT indexdef FROM pg_indexes"
        " WHERE tablename = 'chunks'"
        " AND indexname = 'ix_chunks_embedding_hnsw'"
    )
    with engine.connect() as conn:
        rows = list(conn.execute(q))
    assert rows, "HNSW index ix_chunks_embedding_hnsw missing from chunks"
    defn = rows[0][0]
    assert "hnsw" in defn.lower(), "Index is not HNSW type"
    assert "vector_cosine_ops" in defn, "Index missing vector_cosine_ops"
    engine.dispose()
