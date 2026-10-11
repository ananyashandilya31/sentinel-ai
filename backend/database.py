import logging
from typing import Generator, Tuple, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from backend.config import settings

logger = logging.getLogger(__name__)

# Base class for all ORM models
Base = declarative_base()


def _initialize_engine():
    """
    Initializes SQLAlchemy engine. If PostgreSQL is configured but unreachable
    in local development without Docker, gracefully falls back to local SQLite
    database (sentinel.db) so the SOC dashboard and APIs are fully operational.
    """
    db_url = settings.DATABASE_URL
    connect_args = {}

    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        eng = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
        return eng

    if "postgresql" in db_url:
        connect_args = {"connect_timeout": 2}
        try:
            eng = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            return eng
        except Exception as exc:
            logger.warning(
                "PostgreSQL unreachable (%s). Gracefully falling back to local SQLite 'sentinel.db' for offline development.",
                exc,
            )
            fallback_url = "sqlite:///./sentinel.db"
            eng = create_engine(fallback_url, connect_args={"check_same_thread": False})
            return eng

    return create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)


engine = _initialize_engine()

# Automatically ensure tables exist if running on SQLite
if engine.dialect.name == "sqlite":
    # Import all models to ensure metadata is complete
    import backend.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

# Session factory for database operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
