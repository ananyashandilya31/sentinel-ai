#!/bin/sh
# SentinelAI backend entrypoint.
#
# Waits for PostgreSQL, applies Alembic migrations, seeds the bootstrap
# admin on first boot, then hands off to the CMD (uvicorn).

set -e

echo "[entrypoint] Waiting for database…"
python - <<'PY'
import time, sys
from sqlalchemy import create_engine, text
from backend.config import settings

for attempt in range(1, 31):
    try:
        engine = create_engine(settings.DATABASE_URL, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"[entrypoint] Database ready after {attempt} attempt(s)")
        sys.exit(0)
    except Exception as exc:
        print(f"[entrypoint] Not ready ({attempt}/30): {exc}")
        time.sleep(2)

print("[entrypoint] ERROR: database never became available")
sys.exit(1)
PY

echo "[entrypoint] Applying database migrations…"
alembic -c alembic.ini upgrade head || echo "[entrypoint] WARNING: migration step failed (continuing)"

echo "[entrypoint] Seeding bootstrap admin + synthetic logs…"
python - <<'PY'
from backend.database import SessionLocal
from backend.services import auth_service

session = SessionLocal()
try:
    user = auth_service.ensure_default_admin(session)
    if user:
        print(f"[entrypoint] Admin ready: {user.username}")
    else:
        print("[entrypoint] Users already exist — skipping seed")
finally:
    session.close()
PY

echo "[entrypoint] Starting: $*"
exec "$@"