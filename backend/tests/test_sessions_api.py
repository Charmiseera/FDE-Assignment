"""
Comprehensive tests for sessions and messages endpoints (app/api/v1/endpoints/sessions.py).
Target coverage: >=70% on app/api/v1/endpoints/sessions.py
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import AsyncClient, ASGITransport, Response

from app.main import app
from app.db.session import get_db
from app.db.models import Session, Message, Artifact
from app.rag.retriever import RetrievedChunk


@pytest.fixture
def mock_session_id():
    return uuid.uuid4()


@pytest.fixture
def sample_session(mock_session_id):
    return Session(
        id=mock_session_id,
        title="Test Growth Session",
        provider_at_creation="ollama",
        user_metadata={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_post_message_session_not_found():
    """Posting message to non-existent session returns 404 NOT_FOUND."""
    fake_id = uuid.uuid4()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.post(f"/api/v1/sessions/{fake_id}/messages", json={"content": "Hello"})
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_message_refusal_when_retrieval_empty(mock_session_id, sample_session):
    """When retrieval returns no chunks, assistant emits refusal without calling sidecar."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_session
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    async def set_msg_id(obj):
        if isinstance(obj, Message):
            obj.id = uuid.uuid4()
            obj.created_at = datetime.utcnow()

    mock_db.refresh = AsyncMock(side_effect=set_msg_id)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.api.v1.endpoints.sessions.retrieve_chunks", return_value=[]):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                res = await ac.post(
                    f"/api/v1/sessions/{mock_session_id}/messages",
                    json={"content": "What is the capital of France?"},
                )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "couldn't find anything" in data["data"]["content"]
        assert data["data"]["citations"] == []
        assert data["data"]["artifact_id"] is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_message_grounded_answer(mock_session_id, sample_session):
    """When retrieval succeeds, sidecar is called and returns grounded answer with citations."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_session
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    async def set_msg_id(obj):
        if isinstance(obj, Message):
            obj.id = uuid.uuid4()
            obj.created_at = datetime.utcnow()

    mock_db.refresh = AsyncMock(side_effect=set_msg_id)

    fake_chunks = [
        RetrievedChunk(
            source_file="ep001.txt",
            episode_title="PLG Activation",
            chunk_text="Activation is everything...",
            similarity=0.88,
        )
    ]

    sidecar_response = {
        "content": "Activation is the milestone where users realize value.",
        "citations": [
            {"source_file": "ep001.txt", "episode_title": "PLG Activation"}
        ],
        "artifact": None,
    }

    mock_sidecar_client = AsyncMock()
    mock_sidecar_client.post = AsyncMock(return_value=Response(200, json=sidecar_response, request=MagicMock()))
    mock_sidecar_client.__aenter__.return_value = mock_sidecar_client
    mock_sidecar_client.__aexit__.return_value = None

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.api.v1.endpoints.sessions.retrieve_chunks", return_value=fake_chunks), \
             patch("app.api.v1.endpoints.sessions.httpx.AsyncClient", return_value=mock_sidecar_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                res = await ac.post(
                    f"/api/v1/sessions/{mock_session_id}/messages",
                    json={"content": "What does Lenny say about PLG activation?"},
                )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "Activation is the milestone" in data["data"]["content"]
        assert len(data["data"]["citations"]) == 1
        assert data["data"]["citations"][0]["source_file"] == "ep001.txt"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_message_essay_generation_creates_artifact(mock_session_id, sample_session):
    """Essay request dispatches ship30_essay to sidecar and persists artifact with metadata."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_session
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    art_id = uuid.uuid4()
    msg_id = uuid.uuid4()

    async def fake_flush():
        for call in mock_db.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, Artifact) and getattr(obj, "id", None) is None:
                obj.id = art_id
            elif isinstance(obj, Message) and getattr(obj, "id", None) is None:
                obj.id = msg_id

    mock_db.flush = AsyncMock(side_effect=fake_flush)

    async def set_ids(obj):
        if isinstance(obj, Artifact):
            obj.id = art_id
            obj.created_at = datetime.utcnow()
        elif isinstance(obj, Message):
            obj.id = msg_id
            obj.created_at = datetime.utcnow()

    mock_db.refresh = AsyncMock(side_effect=set_ids)

    fake_chunks = [
        RetrievedChunk(
            source_file="ep001.txt",
            episode_title="PLG Activation",
            chunk_text="Activation is everything...",
            similarity=0.85,
        )
    ]

    sidecar_response = {
        "content": "I've drafted a Ship 30/30 essay based on our discussion.",
        "citations": [{"source_file": "ep001.txt", "episode_title": "PLG Activation"}],
        "artifact": {
            "type": "markdown",
            "title": "The Activation Playbook",
            "content": "# The Activation Playbook\n\n## The Core Mechanism\n\n**Friction is the enemy.**",
            "metadata": {
                "validation_status": {
                    "passed": True,
                    "word_count": 1200,
                    "unmet_criteria": [],
                }
            },
        },
    }

    mock_sidecar_client = AsyncMock()
    mock_sidecar_client.post = AsyncMock(return_value=Response(200, json=sidecar_response, request=MagicMock()))
    mock_sidecar_client.__aenter__.return_value = mock_sidecar_client
    mock_sidecar_client.__aexit__.return_value = None

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch("app.api.v1.endpoints.sessions.retrieve_chunks", return_value=fake_chunks), \
             patch("app.api.v1.endpoints.sessions.httpx.AsyncClient", return_value=mock_sidecar_client):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                res = await ac.post(
                    f"/api/v1/sessions/{mock_session_id}/messages",
                    json={"content": "Turn this into a Ship 30/30 essay"},
                )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["artifact_id"] is not None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_artifact_success(mock_session_id):
    """GET /sessions/{id}/artifacts/{artifact_id} returns artifact with metadata."""
    art_id = uuid.uuid4()
    mock_artifact = Artifact(
        id=art_id,
        session_id=mock_session_id,
        type="markdown",
        title="Test Essay",
        content="# Test Content",
        metadata_sidecar={"validation_status": {"passed": True}},
        created_at=datetime.utcnow(),
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_artifact
    mock_db.execute.return_value = mock_result

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get(f"/api/v1/sessions/{mock_session_id}/artifacts/{art_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["title"] == "Test Essay"
        assert data["data"]["metadata"]["validation_status"]["passed"] is True
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_artifact_not_found(mock_session_id):
    """GET /sessions/{id}/artifacts/{artifact_id} returns 404 when not found."""
    art_id = uuid.uuid4()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            res = await ac.get(f"/api/v1/sessions/{mock_session_id}/artifacts/{art_id}")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"
    finally:
        app.dependency_overrides.clear()
