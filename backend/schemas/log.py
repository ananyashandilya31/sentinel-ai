from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    """Supported security event types in SentinelAI."""
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    DATA_TRANSFER = "DATA_TRANSFER"
    PORT_CONNECT = "PORT_CONNECT"
    PRIVILEGE_CHANGE = "PRIVILEGE_CHANGE"


class LogBase(BaseModel):
    """Shared log properties."""
    user: str = Field(..., min_length=1, max_length=100, description="Username or system account identity")
    ip: str = Field(..., min_length=7, max_length=50, description="Source IPv4 or IPv6 address")
    event_type: EventType = Field(..., description="Classification of the security event")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Network port touched (1-65535)")
    bytes_transferred: Optional[int] = Field(None, ge=0, description="Payload volume in bytes")
    country: str = Field(default="US", min_length=2, max_length=10, description="Source country code")
    session_id: str = Field(..., min_length=1, max_length=100, description="Correlation session identifier")

    @field_validator("country")
    @classmethod
    def normalize_country(cls, v: str) -> str:
        return v.strip().upper()


class LogCreate(LogBase):
    """Payload for ingesting a single security log."""
    timestamp: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC event occurrence timestamp. Defaults to current time if omitted.",
    )


class LogBulkCreate(BaseModel):
    """Payload for batch/bulk ingestion of logs."""
    logs: List[LogCreate] = Field(..., min_length=1, max_length=1000, description="List of logs to ingest (up to 1,000 per request)")


class LogResponse(LogBase):
    """Schema returned when reading a security log from the database."""
    id: str = Field(..., description="Unique UUID identifier for the log event")
    timestamp: datetime = Field(..., description="UTC timestamp of the log event")

    model_config = {
        "from_attributes": True
    }


class PaginatedLogsResponse(BaseModel):
    """Standard paginated container for query results."""
    total: int = Field(..., description="Total matching logs across all pages")
    page: int = Field(..., description="Current active page (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total pages available")
    items: List[LogResponse] = Field(..., description="Logs on the current page")
