from fastapi import APIRouter
from .health import router as health_router
from .logs import router as logs_router
from .incidents import router as incidents_router

# Root v1 API router
api_router = APIRouter(prefix="/api/v1")

# Mount sub-routers
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(logs_router, tags=["Logs Ingestion & Search"])
api_router.include_router(incidents_router, tags=["Incidents & Detection"])

__all__ = ["api_router"]
