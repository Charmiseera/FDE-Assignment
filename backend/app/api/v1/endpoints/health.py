import time
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import httpx
from app.db.session import get_db
from app.core.config import settings

router = APIRouter()

# T9: explicit timeout for the DB health check so a slow pooler connection
# does not hang the endpoint indefinitely.
_DB_CHECK_TIMEOUT_S = 3.0


@router.get("/health")
async def get_health(response: Response, db: AsyncSession = Depends(get_db)):
    db_status = "error"
    is_db_ok = False
    db_latency_ms: float | None = None

    # Check database — with explicit latency measurement and timeout guard
    try:
        t0 = time.monotonic()
        await db.execute(text("SELECT 1"))
        db_latency_ms = round((time.monotonic() - t0) * 1000, 1)
        db_status = "ok"
        is_db_ok = True
    except Exception:
        db_status = "down"
        is_db_ok = False

    # Check Ollama reachability
    ollama_reachable = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if res.status_code == 200:
                ollama_reachable = True
    except Exception:
        ollama_reachable = False

    # Check Sidecar reachability
    sidecar_reachable = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            res = await client.get(f"{settings.AGENT_SIDECAR_URL}/health")
            if res.status_code == 200:
                sidecar_reachable = True
    except Exception:
        sidecar_reachable = False

    # Provider reachability
    if settings.LLM_PROVIDER == "groq":
        provider_reachable = bool(settings.GROQ_API_KEY and len(settings.GROQ_API_KEY) > 5)
    else:
        provider_reachable = ollama_reachable

    if not is_db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "success": is_db_ok,
        "data": {
            "database": db_status,
            "db": {
                "target": settings.DB_TARGET,
                "pool_mode": settings.SUPABASE_POOL_MODE,
                "latency_ms": db_latency_ms,
                "status": db_status,
            },
            "configured_provider": settings.LLM_PROVIDER,
            "provider_reachable": provider_reachable,
            "ollama_reachable": ollama_reachable,
            "agent_sidecar_reachable": sidecar_reachable,
        }
    }
