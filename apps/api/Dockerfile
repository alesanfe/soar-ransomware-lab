
# syntax=docker/dockerfile:1

# ── Stage 1: build ────────────────────────────────────────────────────────────
# Toolchain lives ONLY here — gcc/g++/libpq-dev (and their kernel-header CVEs)
# never reach the runtime image. All wheels land under /install.
FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade build tooling first — pip 24.0/setuptools 79.x ship with the base image
# and carry published CVEs (PYSEC-2026-* tar/wheel extraction flaws, GHSA-xmj3-9gf7-h52w)
RUN pip install --no-cache-dir --upgrade "pip>=26.2" "setuptools>=84.1.0"

# Copy package definition and source first for dependency resolution
COPY pyproject.toml .
COPY requirements.lock .
COPY src ./src
COPY scripts ./scripts

# Install the package plus test, quality and reports dependencies (container is used for tests and reports)
# --timeout: increase per-request timeout for slow networks
# --retries: retry on transient failures
# quality: ruff, bandit, mutmut, etc. for `make quality` and `make mutation`
# reports: matplotlib + numpy for chart generation in e2e_report
# -c requirements.lock: runtime deps resolve to the audited lock versions
# (SSDF PW.4 reproducible builds) — extras (test/quality/reports) resolve free.
RUN pip install --no-cache-dir --timeout 300 --retries 5 --prefix=/install \
    .[test,quality,reports] -c requirements.lock

# Carry the upgraded build tooling into the runtime prefix too — the base
# image ships pip 24.0/setuptools 79.x with published CVEs. --ignore-installed
# forces the copy even though the builder's default site-packages already
# satisfies the spec (prefix installs skip "already satisfied" packages).
RUN pip install --no-cache-dir --prefix=/install --ignore-installed \
    "pip>=26.2" "setuptools>=84.1.0" "wheel>=0.45.0"

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

# Set working directory
WORKDIR /app

# Runtime system deps — apt-get upgrade pulls the Debian security updates the
# dated python:3.11-slim base lags behind. docker-cli only (not docker.io):
# the container talks to the host daemon through the mounted socket — skipping
# the daemon package drops containerd, runc, iptables, git and openssh-client
# (CRITICAL CVE-2026-60002). --no-install-recommends keeps git/ssh out.
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    docker-cli \
    && rm -rf /var/lib/apt/lists/*

# Built Python environment (site-packages + console scripts) from stage 1.
COPY --from=builder /install /usr/local

# The base image's stale dist-infos survive the COPY merge and shadow the
# upgraded packages in both `importlib.metadata` and SBOM/trivy scans.
RUN rm -rf /usr/local/lib/python3.11/site-packages/pip-24.0.dist-info \
           /usr/local/lib/python3.11/site-packages/setuptools-79.0.1.dist-info \
           /usr/local/lib/python3.11/site-packages/wheel-0.42.0.dist-info

# Copy package source and scripts (PYTHONPATH=/app/src shadows site-packages,
# matching the previous single-stage behaviour)
COPY pyproject.toml .
COPY src ./src
COPY scripts ./scripts

# Copy test suite (after install so test-only changes don't invalidate the package layer)
COPY tests ./tests

# Copy static API docs used by main.py root/static-docs handlers
COPY apps/api/api-docs.html ./api-docs.html
COPY apps/api/docs ./docs
COPY .env.example ./.env.example

# Create directories
RUN mkdir -p /app/results /app/backups /app/reports/validation/results

# Setup user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

ENV PYTHONPATH=/app/src

USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application using the composition root factory.
# UVICORN_WORKERS (default 1) enables multi-worker mode — requires
# RATE_LIMIT_BACKEND=redis and WS_TICKET_BACKEND=redis so per-process
# state (rate windows, WS tickets) is shared across workers. WebSocket
# *broadcast fanout* remains per-worker: live-log clients only receive
# events emitted on their own worker (accepted limitation, ADR-0013).
# --no-server-header: the banner is added at uvicorn's protocol layer —
# the middleware's `del headers["server"]` cannot strip it downstream.
CMD ["sh", "-c", "exec uvicorn soar_lab.interfaces.api.composition:create_app --host 0.0.0.0 --port 8000 --factory --no-server-header --workers ${UVICORN_WORKERS:-1}"]
