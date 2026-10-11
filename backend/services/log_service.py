import csv
import math
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, select, func

from backend.models.log import Log
from backend.schemas.log import LogCreate, EventType, PaginatedLogsResponse, LogResponse


def create_log(db: Session, log_data: LogCreate) -> Log:
    """
    Persists a single log entry to the database.
    """
    db_log = Log(
        id=str(uuid.uuid4()),
        timestamp=log_data.timestamp or datetime.now(timezone.utc),
        user=log_data.user,
        ip=log_data.ip,
        event_type=log_data.event_type.value if hasattr(log_data.event_type, "value") else str(log_data.event_type),
        port=log_data.port,
        bytes_transferred=log_data.bytes_transferred,
        country=log_data.country,
        session_id=log_data.session_id,
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def create_logs_bulk(db: Session, logs_data: List[LogCreate]) -> int:
    """
    Bulk persists a list of log entries in a single database transaction.
    Returns the number of successfully inserted logs.
    """
    if not logs_data:
        return 0

    log_objects = [
        Log(
            id=str(uuid.uuid4()),
            timestamp=item.timestamp or datetime.now(timezone.utc),
            user=item.user,
            ip=item.ip,
            event_type=item.event_type.value if hasattr(item.event_type, "value") else str(item.event_type),
            port=item.port,
            bytes_transferred=item.bytes_transferred,
            country=item.country,
            session_id=item.session_id,
        )
        for item in logs_data
    ]

    db.add_all(log_objects)
    db.commit()
    return len(log_objects)


def get_logs(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    user: Optional[str] = None,
    ip: Optional[str] = None,
    event_type: Optional[str] = None,
    search: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> PaginatedLogsResponse:
    """
    Retrieves a paginated list of security logs with multi-field filtering.
    """
    # Enforce safe bounds for pagination
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    query = db.query(Log)

    # Specific filters
    if user:
        query = query.filter(Log.user.ilike(f"%{user}%"))
    if ip:
        query = query.filter(Log.ip.ilike(f"%{ip}%"))
    if event_type:
        query = query.filter(Log.event_type == event_type)
    if start_time:
        query = query.filter(Log.timestamp >= start_time)
    if end_time:
        query = query.filter(Log.timestamp <= end_time)

    # General search across user, ip, and session_id
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Log.user.ilike(search_pattern),
                Log.ip.ilike(search_pattern),
                Log.session_id.ilike(search_pattern),
            )
        )

    # Total matching count
    total = query.count()

    # Pagination with newest first
    offset = (page - 1) * page_size
    items = query.order_by(desc(Log.timestamp)).offset(offset).limit(page_size).all()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedLogsResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=[LogResponse.model_validate(item) for item in items],
    )


def seed_logs_from_csv(db: Session, csv_path: str, max_rows: int = 1000) -> int:
    """
    Reads records from a generated CSV file and inserts them into the database.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found at: {csv_path}")

    logs_to_insert: List[LogCreate] = []

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if len(logs_to_insert) >= max_rows:
                break

            # Parse timestamp if present
            raw_ts = row.get("timestamp")
            parsed_ts = None
            if raw_ts:
                try:
                    parsed_ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                except ValueError:
                    parsed_ts = datetime.now(timezone.utc)

            port_val = row.get("port")
            port = int(port_val) if port_val and port_val.strip() else None

            bytes_val = row.get("bytes_transferred")
            bytes_transferred = int(bytes_val) if bytes_val and bytes_val.strip() else None

            logs_to_insert.append(
                LogCreate(
                    timestamp=parsed_ts,
                    user=row.get("user", "unknown"),
                    ip=row.get("ip", "127.0.0.1"),
                    event_type=EventType(row.get("event_type", "LOGIN_SUCCESS")),
                    port=port,
                    bytes_transferred=bytes_transferred,
                    country=row.get("country", "US"),
                    session_id=row.get("session_id", f"s-{uuid.uuid4().hex[:6]}"),
                )
            )

    return create_logs_bulk(db, logs_to_insert)
