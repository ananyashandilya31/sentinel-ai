"""
Model Trainer for SentinelAI ML Anomaly Detection.

Trains an Isolation Forest on the synthetic security_logs.csv dataset,
evaluates it against the ground-truth 'is_attack' column, and persists
the fitted model to ml/models/isolation_forest.joblib.

Usage (from repo root):
    python -m backend.ml.trainer

Or via the API endpoint:
    POST /api/v1/ml/train
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    classification_report,
    precision_recall_fscore_support,
    roc_auc_score,
)

from backend.ml.feature_engineer import FEATURE_COLUMNS, build_features_from_csv

logger = logging.getLogger(__name__)

# Paths
_REPO_ROOT = Path(__file__).resolve().parents[2]   # sentinel-ai/
MODEL_DIR = _REPO_ROOT / "ml" / "models"
MODEL_PATH = MODEL_DIR / "isolation_forest.joblib"
CSV_PATH = _REPO_ROOT / "data" / "security_logs.csv"

# Isolation Forest hyper-parameters
_IF_PARAMS: dict[str, Any] = {
    "n_estimators": 200,
    "contamination": 0.05,   # ~5% anomalies in synthetic dataset
    "max_samples": "auto",
    "random_state": 42,
    "n_jobs": -1,
}


def train(csv_path: Path | None = None, model_path: Path | None = None) -> dict:
    """
    Train an Isolation Forest on the synthetic dataset and save the model.

    Parameters
    ----------
    csv_path   : override for the default data/security_logs.csv
    model_path : override for the default ml/models/isolation_forest.joblib

    Returns
    -------
    dict with keys:
        model_path, n_samples, n_attack_ips, n_normal_ips,
        precision, recall, f1, roc_auc, report
    """
    csv_path = Path(csv_path) if csv_path else CSV_PATH
    model_path = Path(model_path) if model_path else MODEL_PATH

    if not csv_path.exists():
        raise FileNotFoundError(f"Training CSV not found: {csv_path}")

    logger.info("Loading features from %s …", csv_path)
    df = build_features_from_csv(csv_path)

    if df.empty:
        raise ValueError("Feature DataFrame is empty — check CSV content.")

    X = df[FEATURE_COLUMNS].values.astype(np.float32)
    y_true = df["is_attack"].values.astype(int)   # 1 = attack, 0 = normal

    logger.info(
        "Training on %d IP records (%d attack, %d normal) …",
        len(df),
        y_true.sum(),
        (y_true == 0).sum(),
    )

    clf = IsolationForest(**_IF_PARAMS)
    clf.fit(X)

    # IsolationForest: predict returns +1 (normal) or -1 (anomaly)
    raw_preds = clf.predict(X)
    # Convert to 1=attack, 0=normal
    y_pred = np.where(raw_preds == -1, 1, 0)

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )

    # ROC-AUC using decision_function (lower score = more anomalous → invert)
    scores = -clf.decision_function(X)
    try:
        roc_auc = roc_auc_score(y_true, scores)
    except ValueError:
        roc_auc = 0.0

    report = classification_report(y_true, y_pred, target_names=["normal", "attack"], zero_division=0)

    # Persist model
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, model_path)
    logger.info("Model saved → %s", model_path)

    metrics = {
        "model_path": str(model_path),
        "n_samples": int(len(df)),
        "n_attack_ips": int(y_true.sum()),
        "n_normal_ips": int((y_true == 0).sum()),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "roc_auc": round(float(roc_auc), 4),
        "report": report,
        "feature_columns": FEATURE_COLUMNS,
        "hyperparameters": _IF_PARAMS,
    }

    logger.info(
        "Metrics — P=%.3f R=%.3f F1=%.3f ROC-AUC=%.3f",
        precision, recall, f1, roc_auc,
    )
    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = train()
    print(json.dumps({k: v for k, v in result.items() if k != "report"}, indent=2))
    print("\n--- Classification Report ---")
    print(result["report"])
