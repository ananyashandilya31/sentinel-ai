from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    """Health status and diagnostic info for the database connection."""
    status: str = Field(..., description="'connected' or 'disconnected'")
    engine: str = Field(..., description="Database dialect (e.g. postgresql, sqlite)")
    error: Optional[str] = Field(None, description="Diagnostic error message if disconnected")


class HealthCheckResponse(BaseModel):
    """Schema returned by GET /api/v1/health."""
    status: str = Field(default="ok", description="Overall API service health")
    service: str = Field(default="SentinelAI SOC Engine")
    version: str = Field(..., description="Current application release version")
    environment: str = Field(..., description="Runtime environment (development, production)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of the health check")
    database: DatabaseHealth = Field(..., description="Database connection status")
