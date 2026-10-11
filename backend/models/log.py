import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Index
from backend.database import Base


class Log(Base):
    """
    SQLAlchemy ORM Model representing an ingested security log event.
    Maps directly to the 'logs' table described in Section 7 & 14 of the architecture.
    """
    __tablename__ = "logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    user = Column(String(100), nullable=False, index=True)
    ip = Column(String(50), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    port = Column(Integer, nullable=True)
    bytes_transferred = Column(BigInteger, nullable=True)
    country = Column(String(10), nullable=False, default="US")
    session_id = Column(String(100), nullable=False)

    # Compound indices for efficient time-series and entity-based SOC filtering
    __table_args__ = (
        Index("ix_logs_timestamp_event_type", "timestamp", "event_type"),
        Index("ix_logs_user_timestamp", "user", "timestamp"),
        Index("ix_logs_ip_timestamp", "ip", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Log id={self.id} event={self.event_type} user={self.user} ip={self.ip}>"
