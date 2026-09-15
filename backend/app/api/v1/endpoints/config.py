from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/config")
async def get_config():
    active_model = settings.GROQ_MODEL if settings.LLM_PROVIDER == "groq" else settings.OLLAMA_MODEL
    return {
        "success": True,
        "data": {
            "llm_provider": settings.LLM_PROVIDER,
            "model": active_model,
            "ollama_model": settings.OLLAMA_MODEL,
            "groq_model": settings.GROQ_MODEL,
            "embedding_model": settings.OLLAMA_EMBEDDING_MODEL,
            "groq_available": bool(settings.GROQ_API_KEY),
        }
    }
