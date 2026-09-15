from fastapi import APIRouter
from app.api.v1.endpoints import health, config, sessions

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(config.router, tags=["config"])
api_router.include_router(sessions.router, tags=["sessions"])
