from __future__ import annotations

import pytest
from datetime import datetime, timezone
from backend.models.log import Log
from backend.models.incident import Incident, Evidence
from backend.models.threat_intel import IPReputation


def test_investigate_incident_api_and_caching(client, db_session):
    """Test POST /api/v1/incidents/{id}/investigate, caching, and retrieval."""
    now = datetime.now(timezone.utc)
    log = Log(
        id="log-inv-01",
        timestamp=now,
        user="admin",
        ip="185.23.41.12",
        event_type="LOGIN_FAILED",
        session_id="sess-inv-01",
    )
    incident = Incident(
        id="inc-inv-01",
        title="Brute force attack from 185.23.41.12",
        type="BRUTE_FORCE",
        severity="HIGH",
        status="OPEN",
        created_at=now,
        updated_at=now,
    )
    evidence = Evidence(
        id="ev-inv-01",
        incident_id="inc-inv-01",
        log_id="log-inv-01",
        description="Repeated failed logins",
        created_at=now,
    )
    db_session.add(log)
    db_session.add(incident)
    db_session.add(evidence)
    db_session.commit()

    # 1. Trigger Investigation
    resp1 = client.post("/api/v1/incidents/inc-inv-01/investigate")
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["incident_id"] == "inc-inv-01"
    assert "summary" in data1
    assert len(data1["evidence_points"]) > 0
    assert len(data1["recommended_actions"]) > 0
    assert len(data1["mitre_tactics"]) > 0
    inv_id = data1["id"]

    # 2. Second call should return cached report (same ID)
    resp2 = client.post("/api/v1/incidents/inc-inv-01/investigate")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["id"] == inv_id

    # 3. GET /incidents/{id}/investigation retrieves existing investigation
    resp3 = client.get("/api/v1/incidents/inc-inv-01/investigation")
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["id"] == inv_id

    # 4. GET /incidents/{id} includes latest investigation
    resp4 = client.get("/api/v1/incidents/inc-inv-01")
    assert resp4.status_code == 200
    inc_data = resp4.json()
    assert inc_data["investigation"] is not None
    assert inc_data["investigation"]["id"] == inv_id


def test_investigate_nonexistent_incident(client):
    """Test 404 response when investigating non-existent incident."""
    resp = client.post("/api/v1/incidents/nonexistent-id/investigate")
    assert resp.status_code == 404


def test_get_investigation_not_found(client, db_session):
    """Test 404 response when no investigation has been run yet."""
    now = datetime.now(timezone.utc)
    incident = Incident(
        id="inc-no-inv",
        title="Sample Incident",
        type="PORT_SCAN",
        severity="MEDIUM",
        status="OPEN",
        created_at=now,
        updated_at=now,
    )
    db_session.add(incident)
    db_session.commit()

    resp = client.get("/api/v1/incidents/inc-no-inv/investigation")
    assert resp.status_code == 404
