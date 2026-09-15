import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings


@pytest.mark.asyncio
async def test_get_config():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/config")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "llm_provider" in data["data"]
        assert "model" in data["data"]
        assert "embedding_model" in data["data"]
        assert data["data"]["embedding_model"] == settings.OLLAMA_EMBEDDING_MODEL


@pytest.mark.asyncio
async def test_validation_error_envelope():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Posting to nonexistent session or empty body
        import uuid
        fake_id = str(uuid.uuid4())
        response = await ac.post(f"/api/v1/sessions/{fake_id}/messages", json={"content": "   "})
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "empty" in data["error"]["message"]
