import uuid
import json
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Column, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Investigation(Base):
    """
    SQLAlchemy ORM Model representing an AI-generated incident investigation report.
    Stores structured summary, key evidence bullet points, recommended analyst actions,
    and MITRE ATT&CK tactics produced by the GenAI investigation assistant.
    """
    __tablename__ = "investigations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    severity = Column(String(20), nullable=False)
    summary = Column(Text, nullable=False)
    evidence_points = Column(Text, nullable=False, default="[]")  # JSON-encoded list of bullet points
    recommended_actions = Column(Text, nullable=False, default="[]")  # JSON-encoded list of recommended actions
    mitre_tactics = Column(Text, nullable=False, default="[]")  # JSON-encoded list of MITRE tactics/techniques
    confidence_score = Column(Float, nullable=False, default=0.90)
    model_used = Column(String(50), nullable=False, default="sentinel-soc-analyst-v1")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationship to parent Incident
    incident = relationship("Incident", back_populates="investigations")

    @property
    def evidence_list(self) -> List[str]:
        if not self.evidence_points:
            return []
        try:
            val = json.loads(self.evidence_points)
            return val if isinstance(val, list) else [str(val)]
        except Exception:
            return [self.evidence_points]

    def set_evidence_list(self, items: List[str]) -> None:
        self.evidence_points = json.dumps(items or [])

    @property
    def actions_list(self) -> List[str]:
        if not self.recommended_actions:
            return []
        try:
            val = json.loads(self.recommended_actions)
            return val if isinstance(val, list) else [str(val)]
        except Exception:
            return [self.recommended_actions]

    def set_actions_list(self, items: List[str]) -> None:
        self.recommended_actions = json.dumps(items or [])

    @property
    def mitre_list(self) -> List[str]:
        if not self.mitre_tactics:
            return []
        try:
            val = json.loads(self.mitre_tactics)
            return val if isinstance(val, list) else [str(val)]
        except Exception:
            return [self.mitre_tactics]

    def set_mitre_list(self, items: List[str]) -> None:
        self.mitre_tactics = json.dumps(items or [])

    def __repr__(self) -> str:
        return f"<Investigation id={self.id} incident_id={self.incident_id} model={self.model_used}>"
