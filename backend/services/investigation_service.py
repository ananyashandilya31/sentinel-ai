from __future__ import annotations

import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models.incident import Incident
from backend.models.investigation import Investigation
from backend.schemas.investigation import InvestigationResponse
from backend.ai.prompt_builder import build_structured_evidence
from backend.ai.llm_client import generate_investigation_report

logger = logging.getLogger(__name__)


def get_latest_investigation(db: Session, incident_id: str) -> Optional[InvestigationResponse]:
    """Retrieves the most recent AI investigation report for an incident if one exists."""
    record = (
        db.query(Investigation)
        .filter(Investigation.incident_id == incident_id)
        .order_by(desc(Investigation.created_at))
        .first()
    )
    if not record:
        return None
    return InvestigationResponse.from_orm_model(record)


def investigate_incident(
    db: Session,
    incident_id: str,
    force_refresh: bool = False,
) -> InvestigationResponse:
    """
    Performs AI incident investigation.
    Returns existing cached investigation unless force_refresh is True.
    Builds structured evidence, runs LLM / expert analysis, stores and returns result.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise ValueError(f"Incident with ID '{incident_id}' not found.")

    # Return cached report if available
    existing = (
        db.query(Investigation)
        .filter(Investigation.incident_id == incident_id)
        .order_by(desc(Investigation.created_at))
        .first()
    )

    if existing and not force_refresh:
        return InvestigationResponse.from_orm_model(existing)

    # Build structured evidence from incident, logs, ML predictions & threat intel
    evidence = build_structured_evidence(db, incident)

    # Generate AI investigation report
    analysis = generate_investigation_report(evidence)

    if existing and force_refresh:
        inv = existing
        inv.title = analysis["title"]
        inv.severity = analysis["severity"]
        inv.summary = analysis["summary"]
        inv.set_evidence_list(analysis["evidence_points"])
        inv.set_actions_list(analysis["recommended_actions"])
        inv.set_mitre_list(analysis["mitre_tactics"])
        inv.confidence_score = analysis["confidence_score"]
        inv.model_used = analysis["model_used"]
    else:
        inv = Investigation(
            incident_id=incident.id,
            title=analysis["title"],
            severity=analysis["severity"],
            summary=analysis["summary"],
            confidence_score=analysis["confidence_score"],
            model_used=analysis["model_used"],
        )
        inv.set_evidence_list(analysis["evidence_points"])
        inv.set_actions_list(analysis["recommended_actions"])
        inv.set_mitre_list(analysis["mitre_tactics"])
        db.add(inv)

    db.commit()
    db.refresh(inv)
    return InvestigationResponse.from_orm_model(inv)
