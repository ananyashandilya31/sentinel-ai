import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings
from backend.database import Base, get_db

# In-memory SQLite for instantaneous, self-contained offline testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Provides a fresh transactional test database session per test function."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    FastAPI TestClient with get_db pointed at the test DB.

    Phase 8 added JWT enforcement to write endpoints. Most functional
    tests exercise detection/ingestion logic rather than authorization,
    so this fixture runs them with AUTH_ENABLED=False. Tests that verify
    authentication itself use the `auth_client` fixture instead.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    previous_auth = settings.AUTH_ENABLED
    settings.AUTH_ENABLED = False

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    settings.AUTH_ENABLED = previous_auth


@pytest.fixture(scope="function")
def auth_client(db_session):
    """TestClient with JWT enforcement ON, for authentication/authorization tests."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    previous_auth = settings.AUTH_ENABLED
    settings.AUTH_ENABLED = True

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    settings.AUTH_ENABLED = previous_auth


@pytest.fixture(scope="function")
def admin_token(auth_client):
    """Seeds the default admin and returns a valid Bearer token."""
    auth_client.post("/api/v1/auth/seed")
    res = auth_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin12345"},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


@pytest.fixture(scope="function")
def auth_headers(admin_token):
    """Authorization header for the seeded admin user."""
    return {"Authorization": f"Bearer {admin_token}"}