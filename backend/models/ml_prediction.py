"""
SQLAlchemy ORM model for ML anomaly predictions.

Each row stores the aggregated features and anomaly verdict
for one IP address at the time of evaluation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Index, String, Text

from backend.database import Base


class MLPrediction(Base):
    """
    Stores one Isolation Forest anomaly verdict per (ip, evaluated_at) pair.

    Fields
    ------
    id              UUID primary key
    ip              Source IP that was scored
    anomaly_score   Normalised [0,1] — higher means more anomalous
    is_anomaly      True when the model predicted -1 (anomaly)
    raw_if_score    Raw IsolationForest decision_function value
    feature_vector  JSON-serialised dict of the 7 input features
    evaluated_at    UTC timestamp of when scoring ran
    """
    __tablename__ = "ml_predictions"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    ip = Column(String(50), nullable=False, index=True)
    anomaly_score = Column(Float, nullable=False)
    is_anomaly = Column(Boolean, nullable=False, default=False)
    raw_if_score = Column(Float, nullable=False)
    feature_vector = Column(Text, nullable=False, default="{}")   # JSON string
    evaluated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_ml_predictions_ip_evaluated", "ip", "evaluated_at"),
        Index("ix_ml_predictions_is_anomaly", "is_anomaly"),
    )

    def __repr__(self) -> str:
        return (
            f"<MLPrediction ip={self.ip} score={self.anomaly_score:.3f} "
            f"anomaly={self.is_anomaly}>"
        )
