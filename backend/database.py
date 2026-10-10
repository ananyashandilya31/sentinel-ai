from typing import Generator, Tuple, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from backend.config import settings

# Configure SQLite or PostgreSQL specific connect args
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif "postgresql" in settings.DATABASE_URL:
    # Set 2-second timeout so health checks and tests respond promptly when DB is offline
    connect_args = {"connect_timeout": 2}

# Create SQLAlchemy Engine
# pool_pre_ping=True ensures stale/dropped connections are tested and recycled
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

# Session factory for database operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session per request.
    Ensures the session is cleanly closed even if exceptions occur.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> Tuple[bool, Optional[str]]:
    """
    Performs a lightweight query (SELECT 1) to verify database connectivity.
    Returns (True, None) if successful, or (False, error_details) on failure.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            return True, None
    except Exception as exc:
        return False, str(exc)
