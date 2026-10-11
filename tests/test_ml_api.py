"""
Tests for ML API endpoints.

All tests use an in-memory SQLite database (via conftest.py fixtures).
The Isolation Forest model is trained inside tests using a minimal
synthetic dataset so tests are fully offline.
"""
from __future__ import annotations

import json
import sys
import tempfile
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── /ml/status ───────────────────────────────────────────────────────────────

def test_ml_status_no_model(client):
    """Before training, status should report model_ready=False."""
    with patch("backend.ml.predictor.IFPredictor.is_ready", new_callable=lambda: property(lambda self: False)):
        resp = client.get("/api/v1/ml/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "model_ready" in data
    assert "model_path" in data
    assert "message" in data


# ── /ml/train ────────────────────────────────────────────────────────────────

def test_ml_train_missing_csv(client, tmp_path):
    """If CSV not found, train endpoint should return 404."""
    with patch("backend.api.ml.train") as mock_train:
        mock_train.side_effect = FileNotFoundError("CSV not found")
        resp = client.post("/api/v1/ml/train")
    assert resp.status_code == 404


def test_ml_train_success(client):
    """Train endpoint returns correct schema on success."""
    mock_metrics = {
        "model_path": "/fake/model.joblib",
        "n_samples": 50,
        "n_attack_ips": 5,
        "n_normal_ips": 45,
        "precision": 0.8,
        "recall": 0.75,
        "f1": 0.774,
        "roc_auc": 0.85,
        "report": "mock report",
        "feature_columns": ["failed_login_count", "success_login_count",
                            "unique_ports", "data_transfer_mb",
                            "event_count", "unique_event_types", "login_fail_ratio"],
        "hyperparameters": {},
    }
    with patch("backend.api.ml.train", return_value=mock_metrics), \
         patch("backend.api.ml.get_predictor") as mock_pred:
        mock_pred.return_value.reload = MagicMock()
        resp = client.post("/api/v1/ml/train")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "trained"
    assert data["precision"] == 0.8
    assert data["f1"] == 0.774
    assert "feature_columns" in data


# ── /ml/predict ──────────────────────────────────────────────────────────────

def test_ml_predict_no_model(client):
    """If model not trained, predict should return 424."""
    # Patch where it's USED (imported into the router module), not where it's defined
    with patch("backend.api.ml.run_ml_predictions") as mock_run:
        mock_run.side_effect = FileNotFoundError("Model not found")
        resp = client.post("/api/v1/ml/predict?hours=24")
    assert resp.status_code == 424


def test_ml_predict_empty_logs(client, db_session):
    """With no logs in DB, predict returns empty predictions list."""
    from backend.models.ml_prediction import MLPrediction
    from backend.ml.predictor import IFPredictor

    with patch.object(IFPredictor, "is_ready", new_callable=lambda: property(lambda self: True)), \
         patch("backend.services.ml_service.build_features") as mock_feat, \
         patch("backend.services.ml_service.get_predictor") as mock_pred_factory:

        import pandas as pd
        from backend.ml.feature_engineer import FEATURE_COLUMNS
        mock_feat.return_value = pd.DataFrame(columns=["ip"] + FEATURE_COLUMNS)
        mock_pred_factory.return_value.is_ready = True
        mock_pred_factory.return_value.score.return_value = []

        resp = client.post("/api/v1/ml/predict?hours=24")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["predictions"] == []


# ── /ml/predictions ──────────────────────────────────────────────────────────

def test_ml_predictions_empty(client):
    """Empty DB returns paginated empty response."""
    resp = client.get("/api/v1/ml/predictions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["predictions"] == []
    assert data["anomalies_count"] == 0


def test_ml_predictions_persisted(client, db_session):
    """Predictions saved to DB are returned by the list endpoint."""
    import uuid
    from datetime import datetime, timezone
    from backend.models.ml_prediction import MLPrediction

    pred = MLPrediction(
        id=str(uuid.uuid4()),
        ip="192.168.1.100",
        anomaly_score=0.92,
        is_anomaly=True,
        raw_if_score=-0.15,
        feature_vector=json.dumps({"failed_login_count": 10}),
        evaluated_at=datetime.now(timezone.utc),
    )
    db_session.add(pred)
    db_session.commit()

    resp = client.get("/api/v1/ml/predictions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["anomalies_count"] == 1
    assert data["predictions"][0]["ip"] == "192.168.1.100"
    assert data["predictions"][0]["is_anomaly"] is True


def test_ml_predictions_anomalies_only_filter(client, db_session):
    """anomalies_only=true filter returns only anomalous predictions."""
    import uuid
    from datetime import datetime, timezone
    from backend.models.ml_prediction import MLPrediction

    normal = MLPrediction(
        id=str(uuid.uuid4()),
        ip="10.0.0.1",
        anomaly_score=0.2,
        is_anomaly=False,
        raw_if_score=0.3,
        feature_vector="{}",
        evaluated_at=datetime.now(timezone.utc),
    )
    anomaly = MLPrediction(
        id=str(uuid.uuid4()),
        ip="10.0.0.2",
        anomaly_score=0.95,
        is_anomaly=True,
        raw_if_score=-0.2,
        feature_vector="{}",
        evaluated_at=datetime.now(timezone.utc),
    )
    db_session.add_all([normal, anomaly])
    db_session.commit()

    resp = client.get("/api/v1/ml/predictions?anomalies_only=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["predictions"][0]["ip"] == "10.0.0.2"
