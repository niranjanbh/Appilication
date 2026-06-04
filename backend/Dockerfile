ARG PYTHON_VERSION=3.12-slim-bookworm

# ── Stage 1: base — system packages + non-root user ──────────────────────────
FROM python:${PYTHON_VERSION} AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r kyros && useradd -r -g kyros -u 1000 -m -s /bin/bash kyros
WORKDIR /app

# ── Stage 2: builder — create venv and install Python dependencies ────────────
FROM base AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv

# Copy only manifest files so this layer caches until deps change
COPY pyproject.toml uv.lock ./

# Install uv then use it to install deps without installing the project itself.
# --no-install-project lets us skip the editable install (source is bind-mounted in dev
# or copied in prod); deps land in /opt/venv via UV_PROJECT_ENVIRONMENT.
RUN pip install --quiet uv \
    && UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --frozen --no-dev --no-install-project

# ── Stage 3: dev — all deps including dev/test, source via bind mount ─────────
FROM base AS dev

COPY --from=builder /opt/venv /opt/venv

COPY pyproject.toml uv.lock ./
RUN pip install --quiet uv \
    && UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --frozen --no-install-project

USER kyros
EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Stage 4: prod — self-contained image, source baked in ────────────────────
FROM base AS prod

COPY --from=builder /opt/venv /opt/venv

# Copy source after deps so source changes don't bust the dependency layer
COPY --chown=kyros:kyros . /app/

# Install the project package itself (deps already in venv from builder)
RUN pip install --quiet uv \
    && UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --frozen --no-dev

USER kyros
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
