# syntax=docker/dockerfile:1
# Multi-stage build for gcloud-logs-anomaly-detection

# --- Stage 1: Build & Dependency Installation ---
FROM python:3.14-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# --- Stage 2: Minimal & Hardened Runtime ---
FROM python:3.14-slim AS runtime

LABEL org.opencontainers.image.title="gcloud-logs-anomaly-detection" \
      org.opencontainers.image.description="Machine Learning tool to find anomalies in Google Cloud Logging events" \
      org.opencontainers.image.authors="23skdu@users.noreply.github.com" \
      org.opencontainers.image.url="https://github.com/23skdu/gcloud_logs_anomaly_detection" \
      org.opencontainers.image.source="https://github.com/23skdu/gcloud_logs_anomaly_detection" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/usr/local/bin:$PATH"

# DevSecOps: create non-root user with explicit UID/GID
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash appuser

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application source with least privilege ownership
COPY --chown=appuser:appuser pyproject.toml README.md ./
COPY --chown=appuser:appuser config.py ./
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser gcloud_logs_anomaly_detection/ ./gcloud_logs_anomaly_detection/

# Install the application entrypoint without reinstalling dependencies
RUN pip install --no-cache-dir --no-deps -e .

# Switch to non-root user (using numeric UID:GID for security compliance)
USER 1000:1000

# Healthcheck verifying Python runtime and package integrity
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import gcloud_logs_anomaly_detection; import sys; sys.exit(0)"]

ENTRYPOINT ["gcloud-anomaly"]
CMD ["--help"]
