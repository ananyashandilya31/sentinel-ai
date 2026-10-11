import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.log import (
    LogCreate,
    LogBulkCreate,
    LogResponse,
    PaginatedLogsResponse,
    EventType,
)
from backend.services import log_service, incident_service

router = APIRouter(prefix="/logs", tags=["Logs Ingestion & Search"])


@router.post("", response_model=LogResponse, status_code=status.HTTP_201_CREATED, summary="Ingest Single Security Log")
def ingest_log(log_data: LogCreate, db: Session = Depends(get_db)) -> LogResponse:
    """
    Ingests, validates, and stores a single security event log.
    Automatically evaluates active detection rules.
    """
    try:
        created_log = log_service.create_log(db, log_data)
        # Evaluate detection on recent window for this entity
        incident_service.run_detection_on_logs(db, [created_log])
        return LogResponse.model_validate(created_log)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist log entry: {str(exc)}",
        )


@router.post("/bulk", status_code=status.HTTP_201_CREATED, summary="Bulk Ingest Security Logs")
def ingest_logs_bulk(payload: LogBulkCreate, db: Session = Depends(get_db)):
    """
    Ingests a batch of security event logs in a single transaction.
    Automatically evaluates detection rules on the newly ingested batch.
    """
    try:
        count = log_service.create_logs_bulk(db, payload.logs)
        # Evaluate detection across logs
        incident_service.run_detection_on_logs(db)
        return {
            "status": "success",
            "inserted": count,
            "message": f"Successfully ingested {count} logs.",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk persist log entries: {str(exc)}",
        )


@router.get("", response_model=PaginatedLogsResponse, summary="Query and Filter Security Logs")
def list_logs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    user: Optional[str] = Query(None, description="Filter by user (case-insensitive substring)"),
    ip: Optional[str] = Query(None, description="Filter by source IP (case-insensitive substring)"),
    event_type: Optional[EventType] = Query(None, description="Filter by event type"),
    search: Optional[str] = Query(None, description="General search across user, IP, or session_id"),
    start_time: Optional[datetime] = Query(None, description="Filter logs starting at UTC timestamp"),
    end_time: Optional[datetime] = Query(None, description="Filter logs up to UTC timestamp"),
    db: Session = Depends(get_db),
) -> PaginatedLogsResponse:
    """
    Retrieves security logs sorted in reverse chronological order with optional multi-field filtering.
    """
    event_type_str = event_type.value if event_type else None
    return log_service.get_logs(
        db=db,
        page=page,
        page_size=page_size,
        user=user,
        ip=ip,
        event_type=event_type_str,
        search=search,
        start_time=start_time,
        end_time=end_time,
    )


@router.post("/seed", status_code=status.HTTP_200_OK, summary="Seed Database with Synthetic Logs")
def seed_logs(
    limit: int = Query(250, ge=10, le=2000, description="Max logs to seed into database"),
    db: Session = Depends(get_db),
):
    """
    Populates the database with synthetic logs from the generated dataset in `data/security_logs.csv`
    and immediately executes the rule-based detection engine over them.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    csv_path = os.path.join(project_root, "data", "security_logs.csv")

    if not os.path.exists(csv_path):
        from data.generate_logs import generate_synthetic_logs
        generate_synthetic_logs(output_file=csv_path, total_normal=800)

    try:
        inserted = log_service.seed_logs_from_csv(db, csv_path, max_rows=limit)
        # Run detection engine on seeded logs
        incident_service.run_detection_on_logs(db)
        return {
            "status": "success",
            "count": inserted,
            "message": f"Successfully seeded {inserted} security logs and evaluated detection rules.",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed logs: {str(exc)}",
        )
