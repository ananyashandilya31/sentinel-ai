"""
Feature Engineering for SentinelAI ML Anomaly Detection.

Builds per-entity (IP address) feature vectors from raw Log records
or a CSV file. Features are computed inside a rolling time window so
the model sees *behavioural patterns* rather than individual events.

Feature set (7 numeric features):
    failed_login_count   — number of LOGIN_FAILURE events in the window
    success_login_count  — number of LOGIN_SUCCESS events
    unique_ports         — distinct port values observed
    data_transfer_mb     — total bytes_transferred / 1_048_576
    event_count          — total events in window
    unique_event_types   — cardinality of event_type column
    login_fail_ratio     — failed_login_count / max(event_count, 1)

Each row in the output DataFrame represents one (ip, window) pair.
"""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from backend.models.log import Log

# Ordered list used everywhere — order must never change once model is saved
FEATURE_COLUMNS: list[str] = [
    "failed_login_count",
    "success_login_count",
    "unique_ports",
    "data_transfer_mb",
    "event_count",
    "unique_event_types",
    "login_fail_ratio",
]


def _rows_to_features(rows: list[dict]) -> pd.DataFrame:
    """
    Given a list of dicts with keys:
        ip, event_type, port, bytes_transferred, timestamp
    aggregate per IP and return a DataFrame with FEATURE_COLUMNS.

    If `rows` is empty the function returns an empty DataFrame with the
    correct column schema so downstream code never has to handle None.
    """
    if not rows:
        return pd.DataFrame(columns=["ip"] + FEATURE_COLUMNS)

    groups: dict[str, dict] = defaultdict(lambda: {
        "failed_login_count": 0,
        "success_login_count": 0,
        "ports": set(),
        "bytes": 0,
        "event_count": 0,
        "event_types": set(),
    })

    for r in rows:
        ip = str(r.get("ip", "unknown"))
        g = groups[ip]
        et = str(r.get("event_type", "")).upper()

        g["event_count"] += 1
        g["event_types"].add(et)

        if et == "LOGIN_FAILURE":
            g["failed_login_count"] += 1
        elif et == "LOGIN_SUCCESS":
            g["success_login_count"] += 1

        port = r.get("port")
        if port is not None:
            try:
                g["ports"].add(int(port))
            except (ValueError, TypeError):
                pass

        bt = r.get("bytes_transferred") or 0
        try:
            g["bytes"] += int(bt)
        except (ValueError, TypeError):
            pass

    records = []
    for ip, g in groups.items():
        ec = g["event_count"]
        fl = g["failed_login_count"]
        records.append({
            "ip": ip,
            "failed_login_count": fl,
            "success_login_count": g["success_login_count"],
            "unique_ports": len(g["ports"]),
            "data_transfer_mb": round(g["bytes"] / 1_048_576, 4),
            "event_count": ec,
            "unique_event_types": len(g["event_types"]),
            "login_fail_ratio": round(fl / max(ec, 1), 4),
        })

    return pd.DataFrame(records)


def build_features(logs: list["Log"]) -> pd.DataFrame:
    """
    Build features from a list of SQLAlchemy Log ORM objects.

    Parameters
    ----------
    logs : list[Log]
        Raw Log records retrieved from the database.

    Returns
    -------
    pd.DataFrame
        Columns: ['ip'] + FEATURE_COLUMNS
    """
    rows = [
        {
            "ip": log.ip,
            "event_type": log.event_type,
            "port": log.port,
            "bytes_transferred": log.bytes_transferred,
            "timestamp": log.timestamp,
        }
        for log in logs
    ]
    return _rows_to_features(rows)


def build_features_from_csv(csv_path: str | Path) -> pd.DataFrame:
    """
    Build features from the synthetic security_logs.csv file.

    The CSV is expected to have at minimum:
        ip, event_type, port, bytes_transferred, is_attack

    Returns a DataFrame with FEATURE_COLUMNS plus 'ip' and 'is_attack'
    (aggregated as: is_attack=True if any row for that IP has is_attack=True).
    """
    csv_path = Path(csv_path)
    rows: list[dict] = []

    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append(row)

    if not rows:
        cols = ["ip", "is_attack"] + FEATURE_COLUMNS
        return pd.DataFrame(columns=cols)

    # Build features grouped by IP
    features_df = _rows_to_features(rows)

    # Add ground-truth: mark IP as attack if ANY of its rows has is_attack==True
    attack_ips: set[str] = set()
    for r in rows:
        val = str(r.get("is_attack", "false")).strip().lower()
        if val in ("true", "1", "yes"):
            attack_ips.add(str(r.get("ip", "")))

    features_df["is_attack"] = features_df["ip"].isin(attack_ips)
    return features_df
