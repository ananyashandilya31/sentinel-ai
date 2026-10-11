import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Incident(Base):
    """
    SQLAlchemy ORM Model representing a security incident.
    An incident aggregates one or more detection alerts and correlates triggering logs as evidence.
    """
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(30), nullable=False, default="OPEN", index=True)  # OPEN, INVESTIGATING, RESOLVED, FALSE_POSITIVE
    assigned_to = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    alerts = relationship("Alert", back_populates="incident", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="incident", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Incident id={self.id} type={self.type} severity={self.severity} status={self.status}>"


class Alert(Base):
    """
    SQLAlchemy ORM Model representing an individual detection rule alert.
    """
    __tablename__ = "alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True, index=True)
    rule_name = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    log_id = Column(String(36), ForeignKey("logs.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    incident = relationship("Incident", back_populates="alerts")
    log = relationship("Log", foreign_keys=[log_id])

    def __repr__(self) -> str:
        return f"<Alert id={self.id} rule={self.rule_name} severity={self.severity}>"


class Evidence(Base):
    """
    SQLAlchemy ORM Model representing an evidence link between an Incident and a Log.
    """
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    log_id = Column(String(36), ForeignKey("logs.id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    # Relationships
    incident = relationship("Incident", back_populates="evidence")
    log = relationship("Log", foreign_keys=[log_id])

    def __repr__(self) -> str:
        return f"<Evidence id={self.id} incident_id={self.incident_id} log_id={self.log_id}>"
