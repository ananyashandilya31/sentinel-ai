"""
Model Predictor for SentinelAI ML Anomaly Detection.

Loads the persisted Isolation Forest model and scores new feature vectors.
Follows a lazy-singleton pattern: the model is loaded from disk once on
first access and reused for all subsequent calls within the process.

Usage:
    predictor = get_predictor()
    result = predictor.score(feature_df)
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from backend.ml.feature_engineer import FEATURE_COLUMNS

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = _REPO_ROOT / "ml" / "models" / "isolation_forest.joblib"


@dataclass
class PredictionResult:
    """Per-IP anomaly score returned by the predictor."""
    ip: str
    anomaly_score: float          # Normalised [0, 1] — higher = more anomalous
    is_anomaly: bool              # True when Isolation Forest predicts -1
    raw_if_score: float           # Raw decision_function value (negative = anomalous)
    features: dict = field(default_factory=dict)


class IFPredictor:
    """
    Wraps the trained Isolation Forest for real-time scoring.

    Thread-safe lazy loader — safe to call from multiple FastAPI workers.
    """

    def __init__(self, model_path: Path = MODEL_PATH):
        self._model_path = model_path
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        """Load model from disk (called once)."""
        import joblib  # imported here to keep top-level import lightweight
        if not self._model_path.exists():
            raise FileNotFoundError(
                f"Model not found at {self._model_path}. "
                "Call POST /api/v1/ml/train first."
            )
        self._model = joblib.load(self._model_path)
        logger.info("Isolation Forest model loaded from %s", self._model_path)

    def _ensure_loaded(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._load()

    @property
    def is_ready(self) -> bool:
        """Return True if the model file exists on disk."""
        return self._model_path.exists()

    def score(self, features_df: pd.DataFrame) -> list[PredictionResult]:
        """
        Score a DataFrame produced by `build_features`.

        Parameters
        ----------
        features_df : pd.DataFrame
            Must contain columns: ['ip'] + FEATURE_COLUMNS

        Returns
        -------
        list[PredictionResult]
            One entry per IP in the input DataFrame.
        """
        self._ensure_loaded()

        if features_df.empty:
            return []

        X = features_df[FEATURE_COLUMNS].values.astype(np.float32)

        raw_preds = self._model.predict(X)        # +1 normal / -1 anomaly
        raw_scores = self._model.decision_function(X)  # positive = normal

        # Normalise decision_function to [0, 1] where 1 = most anomalous
        # score_samples returns -decision_function; we further normalise with sigmoid
        anomaly_scores = 1 / (1 + np.exp(raw_scores * 5))

        results: list[PredictionResult] = []
        for i, row in enumerate(features_df.itertuples(index=False)):
            ip = str(row.ip)
            is_anomaly = bool(raw_preds[i] == -1)
            results.append(PredictionResult(
                ip=ip,
                anomaly_score=round(float(anomaly_scores[i]), 4),
                is_anomaly=is_anomaly,
                raw_if_score=round(float(raw_scores[i]), 6),
                features={col: float(getattr(row, col)) for col in FEATURE_COLUMNS},
            ))

        return results

    def reload(self):
        """Force re-load of model from disk (called after re-training)."""
        with self._lock:
            self._model = None
        self._ensure_loaded()


# ── Singleton ─────────────────────────────────────────────────────────────────
_predictor: IFPredictor | None = None
_predictor_lock = threading.Lock()


def get_predictor() -> IFPredictor:
    """Return the process-wide IFPredictor singleton."""
    global _predictor
    if _predictor is None:
        with _predictor_lock:
            if _predictor is None:
                _predictor = IFPredictor()
    return _predictor
