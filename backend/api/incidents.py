from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.incident import (
    IncidentResponse,
    IncidentDetailResponse,
    IncidentUpdate,
    PaginatedIncidentsResponse,
    Severity,
    IncidentStatus,
    IncidentType,
)
from backend.schemas.investigation import InvestigationResponse, InvestigationRequest
from backend.services import incident_service
from backend.services.investigation_service import investigate_incident, get_latest_investigation
from backend.dependencies import require_auth_if_enabled

router = APIRouter(prefix="/incidents", tags=["Incidents & Detection"])


@router.get("", response_model=PaginatedIncidentsResponse, summary="List Security Incidents")
def list_incidents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    severity: Optional[Severity] = Query(None, description="Filter by severity level"),
    status: Optional[IncidentStatus] = Query(None, description="Filter by lifecycle status"),
    type: Optional[IncidentType] = Query(None, description="Filter by incident type"),
    db: Session = Depends(get_db),
) -> PaginatedIncidentsResponse:
    """
    Retrieves a paginated list of security incidents with multi-attribute filtering.
    """
    severity_str = severity.value if severity else None
    status_str = status.value if status else None
    type_str = type.value if type else None

    return incident_service.get_incidents(
        db=db,
        page=page,
        page_size=page_size,
        severity=severity_str,
        status=status_str,
        type=type_str,
    )


@router.get("/{incident_id}", response_model=IncidentDetailResponse, summary="Get Incident Detail with Evidence")
def get_incident_detail(
    incident_id: str,
    db: Session = Depends(get_db),
) -> IncidentDetailResponse:
    """
    Retrieves full details for a specific incident, including associated detection alerts and correlated evidence logs.
    """
    incident = incident_service.get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )
    return incident


@router.patch("/{incident_id}", response_model=IncidentDetailResponse, summary="Update Incident Status or Assignee")
def update_incident(
    incident_id: str,
    payload: IncidentUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_auth_if_enabled),
) -> IncidentDetailResponse:
    """
    Updates the lifecycle status (e.g. OPEN -> INVESTIGATING -> RESOLVED) or assigned analyst for an incident.
    """
    updated = incident_service.update_incident(db, incident_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )
    return updated


@router.post("/evaluate", status_code=status.HTTP_200_OK, summary="Run Detection Engine on Stored Logs")
def evaluate_detection(
    db: Session = Depends(get_db),
    _: None = Depends(require_auth_if_enabled),
):
    """
    Manually triggers evaluation of all detection rules over stored security logs.
    """
    alert_count = incident_service.run_detection_on_logs(db)
    return {
        "status": "success",
        "alerts_triggered": alert_count,
        "message": f"Detection engine executed. Triggered {alert_count} alerts.",
    }


@router.post(
    "/{incident_id}/investigate",
    response_model=InvestigationResponse,
    summary="Trigger AI Incident Investigation (GenAI)",
)
def run_investigation(
    incident_id: str,
    payload: Optional[InvestigationRequest] = None,
    force_refresh: bool = Query(False, description="Whether to regenerate analysis bypassing cache"),
    db: Session = Depends(get_db),
    _: None = Depends(require_auth_if_enabled),
) -> InvestigationResponse:
    """
    Triggers AI-powered incident investigation.
    Extracts structured evidence (logs, timeline, IP reputation, ML scores),
    invokes the LLM / expert SOC synthesis engine, and persists the analysis.
    """
    should_refresh = force_refresh or (payload.force_refresh if payload else False)
    try:
        return investigate_incident(db, incident_id=incident_id, force_refresh=should_refresh)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Investigation failed: {exc}",
        ) from exc


@router.get(
    "/{incident_id}/investigation",
    response_model=InvestigationResponse,
    summary="Get Existing AI Incident Investigation",
)
def get_incident_investigation(
    incident_id: str,
    db: Session = Depends(get_db),
) -> InvestigationResponse:
    """
    Retrieves the latest stored AI investigation report for the specified incident.
    """
    inv = get_latest_investigation(db, incident_id=incident_id)
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No investigation report found for incident '{incident_id}'. Call POST /incidents/{incident_id}/investigate first.",
        )
    return inv
