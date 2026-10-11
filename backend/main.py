from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.api import api_router
from backend.api.ws import handle_alert_websocket

# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="SentinelAI — AI-Powered Security Operations Center (SOC) API Engine",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure Cross-Origin Resource Sharing (CORS) for SOC Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount root WebSocket endpoint for real-time alerting
@app.websocket("/ws/alerts")
async def root_websocket_alerts(websocket: WebSocket):
    await handle_alert_websocket(websocket)

# Mount versioned API routes
app.include_router(api_router)


@app.get("/", tags=["Root"])
def root_status():
    """Welcome and quick link to API documentation."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
