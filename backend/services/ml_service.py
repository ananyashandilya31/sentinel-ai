"""
ML Service — orchestrates feature engineering, prediction, and DB persistence.

Responsibilities:
- Pull recent Log records from DB and build feature vectors
- Call the IFPredictor to score them
- Persist MLPrediction rows, deduplicating within a 1-hour window
- Return results for the API layer
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.ml.feature_engineer import build_features
from backend.ml.predictor import get_predictor
from backend.models.log import Log
from backend.models.ml_prediction import MLPrediction
from backend.schemas.ml_prediction import (
    MLPredictionResponse,
    PaginatedMLPredictionsResponse,
)

logger = logging.getLogger(__name__)


def run_ml_predictions(
    db: Session,
    hours: int = 24,
    save_to_db: bool = True,
) -> list[MLPrediction]:
    """
    Score all logs from the last `hours` hours.

    1. Fetch logs from DB
    2. Build per-IP feature vectors
    3. Score with Isolation Forest
    4. Persist new MLPrediction rows (skip duplicates within 1h)
    5. Return the list of MLPrediction ORM objects that were saved

    Parameters
    ----------
    db         : SQLAlchemy Session
    hours      : rolling window in hours to pull logs from
    save_to_db : set False in tests to skip persistence
    """
    predictor = get_predictor()
    if not predictor.is_ready:
        raise FileNotFoundError(
            "Model not trained yet. Call POST /api/v1/ml/train first."
        )

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    logs = db.query(Log).filter(Log.timestamp >= since).all()

    if not logs:
        logger.info("No logs found in the last %d hours — nothing to score.", hours)
        return []

    features_df = build_features(logs)

    if features_df.empty:
        return []

    results = predictor.score(features_df)

    saved: list[MLPrediction] = []
    now = datetime.now(timezone.utc)
    dedup_window = now - timedelta(hours=1)

    for r in results:
        if save_to_db:
            # Dedup: skip if we already have a prediction for this IP in the last hour
            existing = (
                db.query(MLPrediction)
                .filter(
                    MLPrediction.ip == r.ip,
                    MLPrediction.evaluated_at >= dedup_window,
                )
                .first()
            )
            if existing:
                continue

        pred = MLPrediction(
            ip=r.ip,
            anomaly_score=r.anomaly_score,
            is_anomaly=r.is_anomaly,
            raw_if_score=r.raw_if_score,
            feature_vector=json.dumps(r.features),
            evaluated_at=now,
        )

        if save_to_db:
            db.add(pred)

        saved.append(pred)

    if save_to_db and saved:
        db.commit()
        for pred in saved:
            db.refresh(pred)

    logger.info(
        "ML scoring complete — %d IPs scored, %d saved (%d anomalies)",
        len(results),
        len(saved),
        sum(1 for p in saved if p.is_anomaly),
    )
    return saved


def get_predictions(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    anomalies_only: bool = False,
) -> PaginatedMLPredictionsResponse:
    """
    Return paginated ML predictions from the database.
    """
    query = db.query(MLPrediction).order_by(desc(MLPrediction.evaluated_at))

    if anomalies_only:
        query = query.filter(MLPrediction.is_anomaly.is_(True))

    total = query.count()
    anomalies_count = (
        db.query(MLPrediction).filter(MLPrediction.is_anomaly.is_(True)).count()
    )

    offset = (page - 1) * page_size
    rows = query.offset(offset).limit(page_size).all()

    # Deserialise feature_vector JSON string → dict
    def _to_response(p: MLPrediction) -> MLPredictionResponse:
        try:
            fv = json.loads(p.feature_vector) if p.feature_vector else {}
        except (json.JSONDecodeError, TypeError):
            fv = {}
        return MLPredictionResponse(
            id=p.id,
            ip=p.ip,
            anomaly_score=p.anomaly_score,
            is_anomaly=p.is_anomaly,
            raw_if_score=p.raw_if_score,
            feature_vector=fv,
            evaluated_at=p.evaluated_at,
        )

    return PaginatedMLPredictionsResponse(
        total=total,
        page=page,
        page_size=page_size,
        anomalies_count=anomalies_count,
        predictions=[_to_response(p) for p in rows],
    )
