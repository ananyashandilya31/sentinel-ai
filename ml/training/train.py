"""
Standalone training entry point for the SentinelAI Isolation Forest.

Thin wrapper around `backend.ml.trainer.train()` so the documented
workflow works from the repo root:

    python ml/training/train.py

Trains the model on `data/security_logs.csv`, evaluates it against the
ground-truth `is_attack` labels and persists the fitted model to
`ml/models/isolation_forest.joblib`.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Allow running from anywhere: put repo root on sys.path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.ml.trainer import train  # noqa: E402


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    metrics = train()

    print("\n=== Training complete ===")
    print(json.dumps({k: v for k, v in metrics.items() if k != "report"}, indent=2))
    print("\n--- Classification report ---")
    print(metrics["report"])
    print(f"\nModel saved to: {metrics['model_path']}")


if __name__ == "__main__":
    main()
