"""
Seed a realistic demo state for screenshots: inject the five attack
scenarios with fresh timestamps so the rule engine, threat intel,
AI investigation and ML pages all have data to show.

Usage:
    python scripts/demo_seed.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

API = "http://127.0.0.1:8000/api/v1"


def login() -> str:
    r = httpx.post(f"{API}/auth/login",
                   json={"username": "admin", "password": "admin12345"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def attack_logs(now: datetime) -> list[dict]:
    logs: list[dict] = []

    # 1. Brute force — 10 failures in ~80s
    for i in range(10):
        logs.append({
            "user": "admin", "ip": "185.220.101.5", "event_type": "LOGIN_FAILED",
            "port": 443, "session_id": "s-bf-demo",
            "timestamp": (now + timedelta(seconds=i * 8)).isoformat(),
        })

    # 2. Port scan — 23 distinct ports in 23s
    ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445,
             993, 995, 1433, 1521, 3306, 3389, 5432, 5900, 8080, 8443, 9200]
    for i, port in enumerate(ports):
        logs.append({
            "user": "anonymous", "ip": "45.154.255.88", "event_type": "PORT_CONNECT",
            "port": port, "session_id": f"s-scan-{port}",
            "timestamp": (now + timedelta(seconds=100 + i)).isoformat(),
        })

    # 3. Data exfiltration — 850 MB outbound
    logs.append({
        "user": "alice", "ip": "194.26.29.11", "event_type": "DATA_TRANSFER",
        "port": 443, "bytes_transferred": 891_289_600, "session_id": "s-exfil-demo",
        "timestamp": (now + timedelta(seconds=200)).isoformat(),
    })

    # 4. Account compromise — failures -> success -> large transfer
    base = now + timedelta(seconds=300)
    for i in range(5):
        logs.append({
            "user": "charlie", "ip": "185.23.41.12", "event_type": "LOGIN_FAILED",
            "port": 443, "session_id": "s-comp-demo",
            "timestamp": (base + timedelta(seconds=i * 12)).isoformat(),
        })
    logs.append({
        "user": "charlie", "ip": "185.23.41.12", "event_type": "LOGIN_SUCCESS",
        "port": 443, "session_id": "s-comp-demo",
        "timestamp": (base + timedelta(seconds=70)).isoformat(),
    })
    logs.append({
        "user": "charlie", "ip": "185.23.41.12", "event_type": "DATA_TRANSFER",
        "port": 443, "bytes_transferred": 750_000_000, "session_id": "s-comp-demo",
        "timestamp": (base + timedelta(seconds=110)).isoformat(),
    })

    # 5. Privilege escalation
    logs.append({
        "user": "intern_john", "ip": "192.168.1.99", "event_type": "PRIVILEGE_CHANGE",
        "port": 443, "session_id": "s-priv-demo",
        "timestamp": (now + timedelta(seconds=450)).isoformat(),
    })

    return logs


def main() -> None:
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(timezone.utc)

    # Benign background traffic so counters look realistic
    benign = []
    for i in range(60):
        benign.append({
            "user": ["alice", "bob", "charlie", "devops_sarah"][i % 4],
            "ip": ["192.168.1.10", "10.0.0.15", "192.168.1.42"][i % 3],
            "event_type": "LOGIN_SUCCESS" if i % 3 == 0 else "DATA_TRANSFER",
            "port": 443,
            "bytes_transferred": None if i % 3 == 0 else 8_000_000,
            "session_id": f"s-ben-{i}",
            "timestamp": (now - timedelta(minutes=i * 7)).isoformat(),
        })

    r = httpx.post(f"{API}/logs/bulk", json={"logs": benign + attack_logs(now)},
                   headers=headers, timeout=120)
    r.raise_for_status()
    print(f"ingested: {r.json()['inserted']} logs")

    r = httpx.post(f"{API}/incidents/evaluate", headers=headers, timeout=120)
    print(f"detection: {r.json()['alerts_triggered']} alerts")

    r = httpx.get(f"{API}/incidents?page_size=100", headers=headers, timeout=60)
    data = r.json()
    print(f"incidents: {data['total']}")
    for inc in data["items"][:8]:
        print(f"  [{inc['severity']:8}] {inc['type']:22} {inc['status']:14} {inc['title']}")

    # Run the AI investigation on the most severe incident
    if data["items"]:
        target = data["items"][0]["id"]
        r = httpx.post(f"{API}/incidents/{target}/investigate", headers=headers, timeout=180)
        print(f"investigation: HTTP {r.status_code}")

    r = httpx.post(f"{API}/ml/predict?hours=24", headers=headers, timeout=180)
    if r.status_code == 200:
        p = r.json()
        print(f"ml scored: {p['total']} IPs, {p['anomalies_count']} anomalies")
    else:
        print(f"ml predict: HTTP {r.status_code} {r.text[:200]}")


if __name__ == "__main__":
    main()