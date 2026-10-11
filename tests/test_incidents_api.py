from datetime import datetime, timezone, timedelta


def test_automatic_incident_creation_on_log_ingest(client):
    """
    Verifies that ingesting attack logs via POST /logs/bulk immediately
    triggers detection rules and creates an incident with correlated evidence.
    """
    now = datetime.now(timezone.utc)
    # Craft brute-force attack logs
    logs = [
        {
            "user": "admin",
            "ip": "185.220.101.5",
            "event_type": "LOGIN_FAILED",
            "port": 443,
            "session_id": f"s-{i}",
            "timestamp": (now + timedelta(seconds=i * 5)).isoformat(),
        }
        for i in range(10)
    ]

    bulk_res = client.post("/api/v1/logs/bulk", json={"logs": logs})
    assert bulk_res.status_code == 201

    # Check incidents list
    inc_res = client.get("/api/v1/incidents")
    assert inc_res.status_code == 200
    data = inc_res.json()
    assert data["total"] >= 1

    incident = data["items"][0]
    assert incident["type"] == "BRUTE_FORCE"
    assert incident["severity"] == "HIGH"
    assert incident["status"] == "OPEN"
    assert incident["evidence_count"] >= 8


def test_get_incident_detail_with_evidence(client):
    """
    Verifies GET /api/v1/incidents/{id} returns alerts and attached evidence logs.
    """
    # Trigger an exfiltration attack
    log_payload = {
        "user": "alice",
        "ip": "194.26.29.11",
        "event_type": "DATA_TRANSFER",
        "port": 443,
        "bytes_transferred": 750_000_000,
        "session_id": "s-exfil-test",
    }
    client.post("/api/v1/logs", json=log_payload)

    # Fetch incidents list to find ID
    inc_list = client.get("/api/v1/incidents?type=DATA_EXFILTRATION").json()
    assert inc_list["total"] >= 1
    incident_id = inc_list["items"][0]["id"]

    # Fetch incident detail
    detail_res = client.get(f"/api/v1/incidents/{incident_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == incident_id
    assert detail["severity"] == "CRITICAL"
    assert len(detail["evidence"]) >= 1
    assert len(detail["alerts"]) >= 1

    evidence_item = detail["evidence"][0]
    assert "log" in evidence_item
    assert evidence_item["log"]["user"] == "alice"


def test_update_incident_status_and_assignee(client):
    """
    Verifies PATCH /api/v1/incidents/{id} modifies lifecycle status and analyst assignment.
    """
    # Create incident via privilege escalation
    client.post(
        "/api/v1/logs",
        json={
            "user": "intern_john",
            "ip": "192.168.1.99",
            "event_type": "PRIVILEGE_CHANGE",
            "session_id": "s-priv",
        },
    )

    inc_list = client.get("/api/v1/incidents?type=PRIVILEGE_ESCALATION").json()
    assert inc_list["total"] >= 1
    incident_id = inc_list["items"][0]["id"]

    # Update status to INVESTIGATING and assign to analyst
    patch_payload = {
        "status": "INVESTIGATING",
        "assigned_to": "analyst_sarah",
    }
    patch_res = client.patch(f"/api/v1/incidents/{incident_id}", json=patch_payload)
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["status"] == "INVESTIGATING"
    assert updated["assigned_to"] == "analyst_sarah"


def test_manual_evaluate_endpoint(client):
    """
    Verifies POST /api/v1/incidents/evaluate executes detection scan and returns alert count.
    """
    eval_res = client.post("/api/v1/incidents/evaluate")
    assert eval_res.status_code == 200
    data = eval_res.json()
    assert data["status"] == "success"
    assert "alerts_triggered" in data
