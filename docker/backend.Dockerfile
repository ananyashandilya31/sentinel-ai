# ── SentinelAI Backend (FastAPI) ──────────────────────────────────
# Multi-stage-ish build: wheels are compiled once and cached in a
# builder layer so code edits don't reinstall every dependency.

FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Application code + datasets needed by the ML pipeline
COPY backend/ ./backend/
COPY data/ ./data/
COPY ml/ ./ml/
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY docker/uvicorn_log_config.json /app/docker/uvicorn_log_config.json
RUN chmod +x /usr/local/bin/entrypoint.sh \
    && useradd --create-home --uid 1000 sentinel \
    && chown -R sentinel:sentinel /app
USER sentinel

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=4).status==200 else 1)"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "/app/docker/uvicorn_log_config.json"]