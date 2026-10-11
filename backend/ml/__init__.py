"""
backend/ml — Machine Learning package for SentinelAI.

Modules:
  feature_engineer  — Build per-entity feature vectors from Log records
  trainer           — Train and evaluate the Isolation Forest model
  predictor         — Load saved model and score new feature vectors
"""
from backend.ml.feature_engineer import build_features, build_features_from_csv
from backend.ml.predictor import get_predictor

__all__ = ["build_features", "build_features_from_csv", "get_predictor"]
