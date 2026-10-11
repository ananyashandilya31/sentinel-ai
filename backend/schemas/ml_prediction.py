"""
Pydantic schemas for ML anomaly prediction endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MLPredictionResponse(BaseModel):
    """Single anomaly prediction result returned by the API."""
    id: str
    ip: str
    anomaly_score: float = Field(..., ge=0.0, le=1.0, description="Normalised score [0,1] — higher is more anomalous")
    is_anomaly: bool
    raw_if_score: float
    feature_vector: dict
    evaluated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedMLPredictionsResponse(BaseModel):
    """Paginated list of anomaly predictions."""
    total: int
    page: int
    page_size: int
    anomalies_count: int
    predictions: list[MLPredictionResponse]


class TrainResponse(BaseModel):
    """Returned after a successful model training run."""
    status: str = "trained"
    model_path: str
    n_samples: int
    n_attack_ips: int
    n_normal_ips: int
    precision: float
    recall: float
    f1: float
    roc_auc: float
    feature_columns: list[str]
    report: str


class MLStatusResponse(BaseModel):
    """Current state of the ML model."""
    model_ready: bool
    model_path: str
    message: str
