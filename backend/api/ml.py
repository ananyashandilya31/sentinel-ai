"""
ML API Router — /api/v1/ml/*

Endpoints:
    POST /ml/train          Train (or retrain) the Isolation Forest model
    GET  /ml/status         Check whether a trained model exists
    GET  /ml/predictions    List stored anomaly predictions (paginated)
    POST /ml/predict        Score logs from the last N hours and store results
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import require_auth_if_enabled
from backend.ml import get_predictor
from backend.ml.trainer import MODEL_PATH, train
from backend.schemas.ml_prediction import (
    MLStatusResponse,
    MLPredictionResponse,
    PaginatedMLPredictionsResponse,
    TrainResponse,
)
from backend.services.ml_service import get_predictions, run_ml_predictions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml")


@router.post("/train", response_model=TrainResponse, summary="Train the Isolation Forest model")
def train_model(_: None = Depends(require_auth_if_enabled)):
    """
    Train the Isolation Forest on `data/security_logs.csv`.

    - Reads the synthetic dataset with ground-truth `is_attack` labels
    - Trains with contamination=0.05, 200 estimators, random_state=42
    - Evaluates Precision / Recall / F1 / ROC-AUC against ground truth
    - Saves the fitted model to `ml/models/isolation_forest.joblib`
    - Reloads the in-process predictor singleton
    """
    try:
        metrics = train()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Training failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Training error: {exc}") from exc

    # Force the singleton predictor to reload the freshly trained model
    try:
        get_predictor().reload()
    except Exception:
        pass  # Model was just saved; next request will load it

    return TrainResponse(**metrics)


@router.get("/status", response_model=MLStatusResponse, summary="Check model status")
def model_status():
    """
    Return whether a trained Isolation Forest model exists on disk.
    Call `POST /ml/train` first if `model_ready` is False.
    """
    predictor = get_predictor()
    ready = predictor.is_ready
    return MLStatusResponse(
        model_ready=ready,
        model_path=str(MODEL_PATH),
        message="Model ready — call POST /ml/predict to score logs." if ready
                else "No model found — call POST /ml/train first.",
    )


@router.post("/predict", response_model=PaginatedMLPredictionsResponse, summary="Score recent logs")
def predict(
    hours: int = Query(24, ge=1, le=168, description="Rolling window in hours to score"),
    db: Session = Depends(get_db),
    _: None = Depends(require_auth_if_enabled),
):
    """
    Run the Isolation Forest against all logs from the last `hours` hours.

    - Builds per-IP feature vectors
    - Scores each IP and flags anomalies
    - Persists results (deduplicates within 1-hour window)
    - Returns the predictions that were saved this run
    """
    try:
        saved = run_ml_predictions(db, hours=hours)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Prediction run failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Prediction error: {exc}") from exc

    # Return the fresh batch in a paginated wrapper
    return PaginatedMLPredictionsResponse(
        total=len(saved),
        page=1,
        page_size=len(saved) or 1,
        anomalies_count=sum(1 for p in saved if p.is_anomaly),
        predictions=[
            MLPredictionResponse(
                id=p.id,
                ip=p.ip,
                anomaly_score=p.anomaly_score,
                is_anomaly=p.is_anomaly,
                raw_if_score=p.raw_if_score,
                feature_vector={},
                evaluated_at=p.evaluated_at,
            )
            for p in saved
        ],
    )


@router.get("/predictions", response_model=PaginatedMLPredictionsResponse, summary="List stored predictions")
def list_predictions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    anomalies_only: bool = Query(False, description="Return only anomalous IPs"),
    db: Session = Depends(get_db),
):
    """
    Return paginated anomaly predictions previously stored in the database.
    Use `anomalies_only=true` to filter to flagged IPs only.
    """
    return get_predictions(db, page=page, page_size=page_size, anomalies_only=anomalies_only)
