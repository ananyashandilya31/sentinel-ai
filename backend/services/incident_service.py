import math
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from backend.models.incident import Incident, Alert, Evidence
from backend.models.log import Log
from backend.schemas.incident import (
    IncidentResponse,
    IncidentDetailResponse,
    IncidentUpdate,
    PaginatedIncidentsResponse,
    AlertResponse,
    EvidenceResponse,
)
from backend.schemas.log import LogResponse
from backend.detection.base import DetectedAlert
from backend.detection.engine import default_engine
from backend.services.threat_intel_service import enrich_incident_ips
from backend.services.investigation_service import get_latest_investigation
from backend.ws.manager import ws_manager


def process_alerts(db: Session, alerts: List[DetectedAlert]) -> List[Incident]:
    """
    Correlates detected alerts into Incidents, preventing alert duplication for ongoing attacks.
    Creates corresponding Alert records and links triggering Logs as Evidence.
    """
    if not alerts:
        return []

    created_or_updated: List[Incident] = []

    for alert in alerts:
        # Check if an existing open incident matches this attack type and entity within the last 1 hour
        one_hour_ago = alert.timestamp - timedelta(hours=1)
        existing_incident = (
            db.query(Incident)
            .filter(
                Incident.type == alert.incident_type,
                Incident.status.in_(["OPEN", "INVESTIGATING"]),
                Incident.title.contains(alert.entity_value),
                Incident.created_at >= one_hour_ago,
            )
            .order_by(desc(Incident.created_at))
            .first()
        )

        if existing_incident:
            incident = existing_incident
            incident.updated_at = alert.timestamp or datetime.now(timezone.utc)
            # Escalate severity if incoming alert is higher
            severity_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
            if severity_rank.get(alert.severity, 0) > severity_rank.get(incident.severity, 0):
                incident.severity = alert.severity
        else:
            # Create fresh incident
            incident = Incident(
                id=str(uuid.uuid4()),
                title=alert.title,
                type=alert.incident_type,
                severity=alert.severity,
                status="OPEN",
                created_at=alert.timestamp or datetime.now(timezone.utc),
                updated_at=alert.timestamp or datetime.now(timezone.utc),
            )
            db.add(incident)
            db.flush()  # assign incident.id for foreign keys

        # Create Alert record
        primary_log_id = alert.trigger_log_ids[0] if alert.trigger_log_ids else None
        db_alert = Alert(
            id=str(uuid.uuid4()),
            incident_id=incident.id,
            rule_name=alert.rule_name,
            severity=alert.severity,
            log_id=primary_log_id,
            created_at=alert.timestamp or datetime.now(timezone.utc),
        )
        db.add(db_alert)

        # Attach Evidence for all triggering logs (avoid duplicate evidence for same log_id)
        existing_log_ids = {
            ev.log_id for ev in db.query(Evidence.log_id).filter(Evidence.incident_id == incident.id).all()
        }

        for log_id in alert.trigger_log_ids:
            if log_id not in existing_log_ids:
                db_evidence = Evidence(
                    id=str(uuid.uuid4()),
                    incident_id=incident.id,
                    log_id=log_id,
                    description=alert.description[:250],
                    created_at=alert.timestamp or datetime.now(timezone.utc),
                )
                db.add(db_evidence)
                existing_log_ids.add(log_id)

        created_or_updated.append(incident)

    db.commit()

    # Broadcast newly created or escalated incidents over WebSockets to connected SOC dashboards
    for inc in created_or_updated:
        ws_manager.broadcast_sync({
            "type": "NEW_INCIDENT",
            "incident": {
                "id": inc.id,
                "title": inc.title,
                "type": inc.type,
                "severity": inc.severity,
                "status": inc.status,
                "assigned_to": inc.assigned_to,
                "created_at": inc.created_at.isoformat() if inc.created_at else None,
                "evidence_count": len(inc.evidence) if inc.evidence else 0,
                "alerts_count": len(inc.alerts) if inc.alerts else 0,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    return created_or_updated


def run_detection_on_logs(db: Session, logs: Optional[List[Log]] = None) -> int:
    """
    Evaluates logs against the detection engine and commits generated incidents.
    If logs is None, evaluates the most recent 1,000 logs in the database.
    Returns the count of triggered alerts.
    """
    if logs is None:
        logs = db.query(Log).order_by(Log.timestamp.asc()).limit(1000).all()

    if not logs:
        return 0

    alerts = default_engine.evaluate(logs)
    process_alerts(db, alerts)
    return len(alerts)


def get_incidents(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
) -> PaginatedIncidentsResponse:
    """
    Retrieves paginated incidents with filter support.
    """
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    query = db.query(Incident)

    if severity:
        query = query.filter(Incident.severity == severity)
    if status:
        query = query.filter(Incident.status == status)
    if type:
        query = query.filter(Incident.type == type)

    total = query.count()
    offset = (page - 1) * page_size
    incidents = query.order_by(desc(Incident.created_at)).offset(offset).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    items: List[IncidentResponse] = []
    for inc in incidents:
        items.append(
            IncidentResponse(
                id=inc.id,
                title=inc.title,
                type=inc.type,
                severity=inc.severity,
                status=inc.status,
                assigned_to=inc.assigned_to,
                created_at=inc.created_at,
                updated_at=inc.updated_at,
                evidence_count=len(inc.evidence),
                alerts_count=len(inc.alerts),
            )
        )

    return PaginatedIncidentsResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=items,
    )


def get_incident_by_id(db: Session, incident_id: str) -> Optional[IncidentDetailResponse]:
    """
    Loads full incident details including alerts and evidence logs.
    """
    incident = (
        db.query(Incident)
        .options(
            joinedload(Incident.alerts),
            joinedload(Incident.evidence).joinedload(Evidence.log),
        )
        .filter(Incident.id == incident_id)
        .first()
    )

    if not incident:
        return None

    evidence_responses = []
    for ev in incident.evidence:
        log_resp = LogResponse.model_validate(ev.log) if ev.log else None
        evidence_responses.append(
            EvidenceResponse(
                id=ev.id,
                incident_id=ev.incident_id,
                log_id=ev.log_id,
                description=ev.description,
                created_at=ev.created_at,
                log=log_resp,
            )
        )

    alert_responses = [
        AlertResponse(
            id=al.id,
            incident_id=al.incident_id,
            rule_name=al.rule_name,
            severity=al.severity,
            log_id=al.log_id,
            created_at=al.created_at,
        )
        for al in incident.alerts
    ]

    threat_intel_responses = enrich_incident_ips(db, incident.id)
    latest_inv = get_latest_investigation(db, incident.id)

    return IncidentDetailResponse(
        id=incident.id,
        title=incident.title,
        type=incident.type,
        severity=incident.severity,
        status=incident.status,
        assigned_to=incident.assigned_to,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        evidence_count=len(incident.evidence),
        alerts_count=len(incident.alerts),
        alerts=alert_responses,
        evidence=evidence_responses,
        threat_intel=threat_intel_responses,
        investigation=latest_inv,
    )


def update_incident(
    db: Session,
    incident_id: str,
    update_data: IncidentUpdate,
) -> Optional[IncidentDetailResponse]:
    """
    Updates incident status or analyst assignment.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        return None

    if update_data.status is not None:
        incident.status = update_data.status.value if hasattr(update_data.status, "value") else str(update_data.status)
    if update_data.assigned_to is not None:
        incident.assigned_to = update_data.assigned_to

    incident.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Broadcast update event to all connected dashboards
    ws_manager.broadcast_sync({
        "type": "INCIDENT_UPDATED",
        "incident_id": incident_id,
        "status": incident.status,
        "assigned_to": incident.assigned_to,
        "updated_at": incident.updated_at.isoformat() if incident.updated_at else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return get_incident_by_id(db, incident_id)
