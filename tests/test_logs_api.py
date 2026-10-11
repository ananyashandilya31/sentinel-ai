from datetime import datetime, timezone


def test_ingest_single_log(client):
    """Verifies ingesting a single security log returns 201 Created with generated UUID."""
    payload = {
        "user": "alice",
        "ip": "192.168.1.10",
        "event_type": "LOGIN_SUCCESS",
        "port": 443,
        "bytes_transferred": 1024,
        "country": "us",
        "session_id": "s-alice-101",
    }
    response = client.post("/api/v1/logs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["user"] == "alice"
    assert data["ip"] == "192.168.1.10"
    assert data["event_type"] == "LOGIN_SUCCESS"
    assert data["country"] == "US"  # normalized to uppercase
    assert data["session_id"] == "s-alice-101"


def test_ingest_invalid_log_validation(client):
    """Verifies that invalid payloads are rejected with 422 Unprocessable Entity."""
    # Invalid event type
    payload = {
        "user": "alice",
        "ip": "192.168.1.10",
        "event_type": "INVALID_EVENT_TYPE",
        "session_id": "s-1",
    }
    response = client.post("/api/v1/logs", json=payload)
    assert response.status_code == 422


def test_bulk_ingest_logs(client):
    """Verifies bulk ingesting a list of logs in a single request."""
    logs = [
        {
            "user": f"user_{i}",
            "ip": f"10.0.0.{i}",
            "event_type": "PORT_CONNECT",
            "port": 80,
            "session_id": f"s-{i}",
        }
        for i in range(5)
    ]
    response = client.post("/api/v1/logs/bulk", json={"logs": logs})
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["inserted"] == 5

    # Confirm all 5 are queryable
    list_res = client.get("/api/v1/logs")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 5


def test_filter_logs_by_user_and_event_type(client):
    """Verifies multi-field filtering by user and event_type."""
    logs = [
        {"user": "alice", "ip": "192.168.1.10", "event_type": "LOGIN_SUCCESS", "session_id": "s1"},
        {"user": "alice", "ip": "192.168.1.10", "event_type": "LOGIN_FAILED", "session_id": "s2"},
        {"user": "bob", "ip": "192.168.1.20", "event_type": "LOGIN_FAILED", "session_id": "s3"},
    ]
    client.post("/api/v1/logs/bulk", json={"logs": logs})

    # Filter event_type=LOGIN_FAILED
    res1 = client.get("/api/v1/logs?event_type=LOGIN_FAILED")
    assert res1.json()["total"] == 2

    # Filter user=alice
    res2 = client.get("/api/v1/logs?user=alice")
    assert res2.json()["total"] == 2

    # Filter both user=alice and event_type=LOGIN_FAILED
    res3 = client.get("/api/v1/logs?user=alice&event_type=LOGIN_FAILED")
    assert res3.json()["total"] == 1
    assert res3.json()["items"][0]["session_id"] == "s2"


def test_logs_pagination(client):
    """Verifies offset/limit server-side pagination."""
    logs = [
        {"user": f"user_{i}", "ip": "10.0.0.1", "event_type": "PORT_CONNECT", "session_id": f"s-{i}"}
        for i in range(15)
    ]
    client.post("/api/v1/logs/bulk", json={"logs": logs})

    # Page 1 of 5
    page1 = client.get("/api/v1/logs?page=1&page_size=5").json()
    assert page1["total"] == 15
    assert page1["page"] == 1
    assert page1["page_size"] == 5
    assert page1["total_pages"] == 3
    assert len(page1["items"]) == 5

    # Page 2 of 5
    page2 = client.get("/api/v1/logs?page=2&page_size=5").json()
    assert page2["page"] == 2
    assert len(page2["items"]) == 5


def test_search_logs(client):
    """Verifies general search across IP, username, and session_id."""
    logs = [
        {"user": "devops_sarah", "ip": "172.16.0.5", "event_type": "LOGIN_SUCCESS", "session_id": "session-unique-xyz"},
        {"user": "intern_john", "ip": "172.16.0.9", "event_type": "LOGIN_SUCCESS", "session_id": "s-123"},
    ]
    client.post("/api/v1/logs/bulk", json={"logs": logs})

    # Search by part of session_id
    search_session = client.get("/api/v1/logs?search=unique-xyz").json()
    assert search_session["total"] == 1
    assert search_session["items"][0]["user"] == "devops_sarah"

    # Search by IP substring
    search_ip = client.get("/api/v1/logs?search=172.16.0.9").json()
    assert search_ip["total"] == 1
    assert search_ip["items"][0]["user"] == "intern_john"
