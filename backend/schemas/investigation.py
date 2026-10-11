from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class InvestigationRequest(BaseModel):
    force_refresh: bool = Field(False, description="Whether to bypass cache and regenerate the AI investigation")


class StructuredEvidence(BaseModel):
    """Structured evidence payload built from database entities and supplied to the LLM."""
    incident_id: str
    title: str
    type: str
    severity: str
    affected_users: List[str] = Field(default_factory=list)
    source_ips: List[str] = Field(default_factory=list)
    event_types: List[str] = Field(default_factory=list)
    events_count: int = 0
    time_range_start: Optional[str] = None
    time_range_end: Optional[str] = None
    max_anomaly_score: Optional[float] = None
    threat_intel_context: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_logs: List[Dict[str, Any]] = Field(default_factory=list)


class InvestigationResponse(BaseModel):
    """Schema representing an AI-generated incident investigation analysis."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    incident_id: str
    title: str
    severity: str
    summary: str
    evidence_points: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    mitre_tactics: List[str] = Field(default_factory=list)
    confidence_score: float = Field(0.90, ge=0.0, le=1.0)
    model_used: str
    created_at: datetime

    @classmethod
    def from_orm_model(cls, model_obj) -> InvestigationResponse:
        evidence = model_obj.evidence_list if hasattr(model_obj, "evidence_list") else []
        actions = model_obj.actions_list if hasattr(model_obj, "actions_list") else []
        mitre = model_obj.mitre_list if hasattr(model_obj, "mitre_list") else []
        return cls(
            id=model_obj.id,
            incident_id=model_obj.incident_id,
            title=model_obj.title,
            severity=model_obj.severity,
            summary=model_obj.summary,
            evidence_points=evidence,
            recommended_actions=actions,
            mitre_tactics=mitre,
            confidence_score=model_obj.confidence_score,
            model_used=model_obj.model_used,
            created_at=model_obj.created_at,
        )
