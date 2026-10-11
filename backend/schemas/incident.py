from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from backend.schemas.log import LogResponse
from backend.schemas.threat_intel import IPReputationResponse
from backend.schemas.investigation import InvestigationResponse


class Severity(str, Enum):
    """Incident and alert severity classifications."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, Enum):
    """Lifecycle status of a security incident."""
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class IncidentType(str, Enum):
    """Categorization of detected attacks and anomalies."""
    BRUTE_FORCE = "BRUTE_FORCE"
    PORT_SCAN = "PORT_SCAN"
    DATA_EXFILTRATION = "DATA_EXFILTRATION"
    ACCOUNT_COMPROMISE = "ACCOUNT_COMPROMISE"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"
    ANOMALY = "ANOMALY"


class AlertResponse(BaseModel):
    """Schema for individual detection rule alert."""
    id: str
    incident_id: Optional[str] = None
    rule_name: str
    severity: Severity
    log_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceResponse(BaseModel):
    """Schema for correlated evidence logs attached to an incident."""
    id: str
    incident_id: str
    log_id: str
    description: str
    created_at: datetime
    log: Optional[LogResponse] = None

    model_config = {"from_attributes": True}


class IncidentResponse(BaseModel):
    """Schema returned for lists of incidents."""
    id: str
    title: str
    type: IncidentType
    severity: Severity
    status: IncidentStatus
    assigned_to: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    evidence_count: int = 0
    alerts_count: int = 0

    model_config = {"from_attributes": True}


class IncidentDetailResponse(IncidentResponse):
    """Comprehensive incident view including linked alerts, evidence logs, threat intel, and AI investigation."""
    alerts: List[AlertResponse] = []
    evidence: List[EvidenceResponse] = []
    threat_intel: List[IPReputationResponse] = []
    investigation: Optional[InvestigationResponse] = None

    model_config = {"from_attributes": True}


class IncidentUpdate(BaseModel):
    """Payload for updating incident status or analyst assignment."""
    status: Optional[IncidentStatus] = None
    assigned_to: Optional[str] = Field(None, max_length=100)


class PaginatedIncidentsResponse(BaseModel):
    """Paginated collection of incidents."""
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[IncidentResponse]
