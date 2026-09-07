FROM python:3.14-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.14-slim

LABEL author=23skdu@users.noreply.github.com

RUN groupadd --uid 1000 appuser && useradd --uid 1000 --gid appuser --create-home appuser

COPY --from=builder /install /usr/local

WORKDIR /app

COPY config.py gcloud_logs_detect.py llmtest.py gcloud_logs_llmsummary.py gcloud_event_create.py ./
COPY gcloud_logs_anomaly_detection/ ./gcloud_logs_anomaly_detection/

ENV PYTHONUNBUFFERED=1

USER appuser

HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

ENTRYPOINT ["python"]
CMD ["gcloud_logs_detect.py", "--help"]
