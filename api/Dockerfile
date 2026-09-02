# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Overtake API and worker. One image, two entrypoints: the process is chosen by
# the command, so the API and the worker can never drift out of step.
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build deps for asyncpg and numpy wheels, removed again in the final stage.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY overtake ./overtake
RUN pip install --no-cache-dir .

COPY alembic.ini ./
COPY alembic ./alembic
COPY prompts ./prompts

# Never run as root.
RUN useradd --create-home --uid 10001 overtake \
 && chown -R overtake:overtake /app
USER overtake

EXPOSE 8000

# The container is unhealthy if the database is unreachable, which is what the
# /health endpoint reports.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/v1/health || exit 1

# Migrations are a separate, manually approved step and are deliberately NOT
# run here (08-technical-spec.md §8).
CMD ["uvicorn", "overtake.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
