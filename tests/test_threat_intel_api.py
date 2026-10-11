from __future__ import annotations

import pytest
from datetime import datetime, timezone
from backend.models.log import Log
from backend.models.incident import Incident, Evidence
from backend.models.threat_intel import IPReputation
from backend.services.threat_intel_service import seed_threat_intel_database


def test_seed_api(client):
    """Test POST /api/v1/threat-intel/seed."""
    resp = client.post("/api/v1/threat-intel/seed")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["seeded_count"] > 0


def test_get_threat_intel_by_ip(client):
    """Test GET /api/v1/threat-intel/{ip} for seeded IP."""
    client.post("/api/v1/threat-intel/seed")
    resp = client.get("/api/v1/threat-intel/45.154.255.88")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ip"] == "45.154.255.88"
    assert data["reputation"] == "MALICIOUS"
    assert data["risk_score"] >= 90
    assert data["country"] == "Russia"
    assert isinstance(data["threat_types"], list)


def test_get_threat_intel_dynamic(client):
    """Test GET /api/v1/threat-intel/{ip} for unseen IP."""
    resp = client.get("/api/v1/threat-intel/203.0.113.195")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ip"] == "203.0.113.195"
    assert "reputation" in data
    assert "risk_score" in data


def test_list_threat_intel(client):
    """Test GET /api/v1/threat-intel with filtering."""
    client.post("/api/v1/threat-intel/seed")
    resp = client.get("/api/v1/threat-intel?page=1&page_size=10&reputation=MALICIOUS")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["reputation"] == "MALICIOUS"


def test_batch_lookup_api(client):
    """Test POST /api/v1/threat-intel/batch."""
    client.post("/api/v1/threat-intel/seed")
    resp = client.post(
        "/api/v1/threat-intel/batch",
        json={"ips": ["45.154.255.88", "185.220.101.5", "1.1.1.1"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["results"]) == 3


def test_incident_detail_with_threat_intel(client, db_session):
    """Test GET /api/v1/incidents/{id} includes threat_intel array."""
    seed_threat_intel_database(db_session)

    now = datetime.now(timezone.utc)
    log = Log(
        id="log-inc-ti-01",
        timestamp=now,
        user="attacker",
        ip="45.154.255.88",
        event_type="LOGIN_FAILED",
        session_id="sess-api-ti-01",
    )
    incident = Incident(
        id="inc-api-ti-01",
        title="Brute Force from 45.154.255.88",
        type="BRUTE_FORCE",
        severity="HIGH",
        status="OPEN",
        created_at=now,
        updated_at=now,
    )
    evidence = Evidence(
        id="ev-inc-ti-01",
        incident_id="inc-api-ti-01",
        log_id="log-inc-ti-01",
        description="Triggering login failed attempt",
        created_at=now,
    )
    db_session.add(log)
    db_session.add(incident)
    db_session.add(evidence)
    db_session.commit()

    resp = client.get("/api/v1/incidents/inc-api-ti-01")
    assert resp.status_code == 200
    data = resp.json()
    assert "threat_intel" in data
    assert len(data["threat_intel"]) >= 1
    ti = data["threat_intel"][0]
    assert ti["ip"] == "45.154.255.88"
    assert ti["reputation"] == "MALICIOUS"
    assert ti["risk_score"] >= 90
