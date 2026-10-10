from fastapi import APIRouter
from .health import router as health_router

# Root v1 API router
api_router = APIRouter(prefix="/api/v1")

# Mount sub-routers
api_router.include_router(health_router, tags=["Health"])

__all__ = ["api_router"]
