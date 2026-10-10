from datetime import datetime, timezone
from fastapi import APIRouter
from backend.config import settings
from backend.database import check_db_connection, engine
from backend.schemas.health import HealthCheckResponse, DatabaseHealth

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse, summary="Service & Database Health Status")
def get_health() -> HealthCheckResponse:
    """
    Checks the status of the SentinelAI backend service and active database connection.
    Executes a SELECT 1 ping against the database to confirm live connectivity.
    """
    db_connected, db_error = check_db_connection()
    dialect_name = engine.dialect.name

    db_health = DatabaseHealth(
        status="connected" if db_connected else "disconnected",
        engine=dialect_name,
        error=db_error if not db_connected else None,
    )

    return HealthCheckResponse(
        status="ok" if db_connected else "degraded",
        service="SentinelAI SOC Engine",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        database=db_health,
    )
