# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# TWS E-Commerce backend (FastAPI, async SQLAlchemy + asyncpg)
# ---------------------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# curl backs the container healthcheck. asyncpg ships wheels, so no libpq needed.
RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/*

# Pinned so image builds resolve dependencies the same way the local .venv does,
# rather than drifting with whatever pip the base image happens to ship.
RUN pip install --no-cache-dir --upgrade pip==26.2.1

COPY requirements.txt requirements-dev.txt ./
# The dev image installs test tooling so `docker compose exec api pytest` works.
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
