"""
Tests for the ML feature engineering module.

Verifies:
  - Feature columns are correct and complete
  - Per-IP aggregation logic (failed logins, ports, bytes, ratios)
  - Empty input handling
  - CSV loading (using the real data/security_logs.csv)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

# Make sure 'backend' package is on the path when running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.ml.feature_engineer import (
    FEATURE_COLUMNS,
    build_features_from_csv,
)

_CSV = Path(__file__).resolve().parents[1] / "data" / "security_logs.csv"


# ── Helpers ───────────────────────────────────────────────────────────────────

class _FakeLog:
    """Lightweight stand-in for a SQLAlchemy Log object."""
    def __init__(self, ip, event_type, port=None, bytes_transferred=None, timestamp=None):
        self.ip = ip
        self.event_type = event_type
        self.port = port
        self.bytes_transferred = bytes_transferred
        self.timestamp = timestamp


# ── Feature column contract ───────────────────────────────────────────────────

def test_feature_columns_order():
    """FEATURE_COLUMNS must never change order once model is saved."""
    assert FEATURE_COLUMNS == [
        "failed_login_count",
        "success_login_count",
        "unique_ports",
        "data_transfer_mb",
        "event_count",
        "unique_event_types",
        "login_fail_ratio",
    ]


# ── build_features (from ORM objects) ────────────────────────────────────────

def test_build_features_empty():
    from backend.ml.feature_engineer import build_features
    df = build_features([])
    assert df.empty
    # Should still have the right columns
    assert set(FEATURE_COLUMNS).issubset(set(df.columns))


def test_build_features_single_ip():
    from backend.ml.feature_engineer import build_features
    logs = [
        _FakeLog("1.2.3.4", "LOGIN_FAILURE"),
        _FakeLog("1.2.3.4", "LOGIN_FAILURE"),
        _FakeLog("1.2.3.4", "LOGIN_SUCCESS"),
        _FakeLog("1.2.3.4", "PORT_SCAN", port=22),
        _FakeLog("1.2.3.4", "DATA_TRANSFER", bytes_transferred=1_048_576),  # 1 MB
    ]
    df = build_features(logs)
    assert len(df) == 1
    row = df.iloc[0]
    assert row["ip"] == "1.2.3.4"
    assert row["failed_login_count"] == 2
    assert row["success_login_count"] == 1
    assert row["event_count"] == 5
    assert row["data_transfer_mb"] == pytest.approx(1.0, rel=1e-3)
    assert row["unique_ports"] == 1
    assert row["login_fail_ratio"] == pytest.approx(2 / 5, rel=1e-3)


def test_build_features_multiple_ips():
    from backend.ml.feature_engineer import build_features
    logs = [
        _FakeLog("10.0.0.1", "LOGIN_FAILURE"),
        _FakeLog("10.0.0.2", "LOGIN_SUCCESS"),
        _FakeLog("10.0.0.3", "PORT_SCAN", port=80),
    ]
    df = build_features(logs)
    assert len(df) == 3
    ips = set(df["ip"].tolist())
    assert ips == {"10.0.0.1", "10.0.0.2", "10.0.0.3"}


def test_build_features_port_dedup():
    """Same port accessed multiple times should count as 1 unique port."""
    from backend.ml.feature_engineer import build_features
    logs = [
        _FakeLog("5.5.5.5", "PORT_SCAN", port=443),
        _FakeLog("5.5.5.5", "PORT_SCAN", port=443),
        _FakeLog("5.5.5.5", "PORT_SCAN", port=80),
    ]
    df = build_features(logs)
    assert df.iloc[0]["unique_ports"] == 2


# ── build_features_from_csv ───────────────────────────────────────────────────

@pytest.mark.skipif(not _CSV.exists(), reason="security_logs.csv not found")
def test_csv_features_schema():
    df = build_features_from_csv(_CSV)
    assert not df.empty
    for col in FEATURE_COLUMNS:
        assert col in df.columns, f"Missing column: {col}"
    assert "ip" in df.columns
    assert "is_attack" in df.columns


@pytest.mark.skipif(not _CSV.exists(), reason="security_logs.csv not found")
def test_csv_features_attack_ips_present():
    """At least some IPs should be flagged as attack in the synthetic data."""
    df = build_features_from_csv(_CSV)
    assert df["is_attack"].sum() > 0, "No attack IPs found — check CSV is_attack column"


@pytest.mark.skipif(not _CSV.exists(), reason="security_logs.csv not found")
def test_csv_features_no_nulls():
    df = build_features_from_csv(_CSV)
    for col in FEATURE_COLUMNS:
        assert df[col].isnull().sum() == 0, f"Null values in feature column: {col}"


@pytest.mark.skipif(not _CSV.exists(), reason="security_logs.csv not found")
def test_csv_features_ratio_bounded():
    """login_fail_ratio must be in [0, 1]."""
    df = build_features_from_csv(_CSV)
    assert (df["login_fail_ratio"] >= 0).all()
    assert (df["login_fail_ratio"] <= 1).all()
