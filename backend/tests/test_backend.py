import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.exc import OperationalError
from app.main import app
from app.core.config import settings
from app.db.session import get_db
from app.db.models import Session, Message


# ────────────────────────────────────────────────
# Health-check tests
# ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check_200_when_db_up():
    """Health check returns 200 when DB is reachable."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["database"] == "ok"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check_503_when_db_down():
    """Health check returns 503 when Postgres is stopped or unreachable."""
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=OperationalError("connection refused", {}, None))

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/health")
        assert res.status_code == 503
        data = res.json()
        assert data["success"] is False
        assert data["data"]["database"] == "down"
    finally:
        app.dependency_overrides.clear()


# ────────────────────────────────────────────────
# Provider toggle test (no code change needed)
# ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_provider_toggle_config_without_code_changes():
    """Switching LLM_PROVIDER reflects immediately in GET /api/v1/config without code change."""
    original_provider = settings.LLM_PROVIDER
    transport = ASGITransport(app=app)

    try:
        settings.LLM_PROVIDER = "groq"
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/config")
        assert res.status_code == 200
        data = res.json()
        assert data["data"]["llm_provider"] == "groq"
        assert data["data"]["model"] == settings.GROQ_MODEL
        assert data["data"]["embedding_model"] == settings.OLLAMA_EMBEDDING_MODEL

        settings.LLM_PROVIDER = "ollama"
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/config")
        assert res.status_code == 200
        data = res.json()
        assert data["data"]["llm_provider"] == "ollama"
        assert data["data"]["model"] == settings.OLLAMA_MODEL
        assert data["data"]["embedding_model"] == settings.OLLAMA_EMBEDDING_MODEL
    finally:
        settings.LLM_PROVIDER = original_provider


# ────────────────────────────────────────────────
# Session create → list → fetch-messages round-trip
# ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_session_create_list_messages_round_trip():
    """Session create → list → fetch messages round trip (all mocked DB)."""
    test_session_id = uuid.uuid4()
    mock_session = Session(
        id=test_session_id,
        title="Test Growth Session",
        provider_at_creation="ollama",
        user_metadata={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # ── create session mock ──
    create_db = AsyncMock()
    create_db.add = MagicMock()
    create_db.commit = AsyncMock()
    create_db.flush = AsyncMock()

    async def set_id(obj):
        """Simulate refresh populating the auto-generated id/timestamps."""
        if isinstance(obj, Session):
            obj.id = test_session_id
            obj.created_at = datetime.utcnow()
            obj.updated_at = datetime.utcnow()

    create_db.refresh = AsyncMock(side_effect=set_id)

    # ── list sessions mock ──
    list_scalar = MagicMock()
    list_scalar.scalars.return_value.all.return_value = [mock_session]
    list_db = AsyncMock()
    list_db.execute = AsyncMock(return_value=list_scalar)

    # ── messages mock ──
    msg_scalar = MagicMock()
    msg_scalar.scalar_one_or_none.return_value = mock_session
    msg_scalar.scalars.return_value.all.return_value = []
    msgs_db = AsyncMock()
    msgs_db.execute = AsyncMock(return_value=msg_scalar)

    transport = ASGITransport(app=app)

    # 1. Create — override must be an async generator function (not a coroutine)
    async def override_create():
        yield create_db

    app.dependency_overrides[get_db] = override_create
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post("/api/v1/sessions", json={})
    assert create_res.status_code == 201
    assert create_res.json()["success"] is True

    # 2. List
    async def override_list():
        yield list_db

    app.dependency_overrides[get_db] = override_list
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        list_res = await client.get("/api/v1/sessions")
    assert list_res.status_code == 200
    assert list_res.json()["success"] is True
    assert len(list_res.json()["data"]) >= 1

    # 3. Fetch messages
    async def override_msgs():
        yield msgs_db

    app.dependency_overrides[get_db] = override_msgs
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        msg_res = await client.get(f"/api/v1/sessions/{test_session_id}/messages")
    assert msg_res.status_code == 200
    assert msg_res.json()["success"] is True
    assert isinstance(msg_res.json()["data"], list)

    app.dependency_overrides.clear()
