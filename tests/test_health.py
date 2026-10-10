import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    """Provides a TestClient instance for testing API endpoints."""
    return TestClient(app)


def test_root_endpoint(client):
    """Verifies that GET / returns a 200 OK status and welcome payload."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "SentinelAI"
    assert data["status"] == "online"
    assert "version" in data
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/v1/health"


def test_health_endpoint_structure(client):
    """
    Verifies that GET /api/v1/health returns a structured health payload
    adhering to the HealthCheckResponse schema.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()

    # Core health response attributes
    assert "status" in data
    assert data["service"] == "SentinelAI SOC Engine"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data

    # Database health sub-object
    assert "database" in data
    db_info = data["database"]
    assert "status" in db_info
    assert db_info["status"] in ["connected", "disconnected"]
    assert "engine" in db_info


def test_health_endpoint_with_mocked_db_connected(monkeypatch, client):
    """Verifies health endpoint reports status='ok' when database is connected."""
    monkeypatch.setattr("backend.api.health.check_db_connection", lambda: (True, None))

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"]["status"] == "connected"
    assert data["database"]["error"] is None


def test_health_endpoint_with_mocked_db_disconnected(monkeypatch, client):
    """Verifies health endpoint reports status='degraded' when database is disconnected."""
    monkeypatch.setattr("backend.api.health.check_db_connection", lambda: (False, "Connection refused"))

    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"]["status"] == "disconnected"
    assert data["database"]["error"] == "Connection refused"
