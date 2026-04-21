FROM python:3.11-slim
LABEL author=23skdu@users.noreply.github.com

WORKDIR /app

RUN apt-get update && apt-get -y upgrade && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    tzdata==2025.2 \
    pandas==2.3.3 \
    scikit-learn==1.8.0 \
    google-cloud-logging==3.12.1 \
    seaborn==0.13.2 \
    matplotlib==3.10.0 \
    langchain==0.3.17 \
    langchain-google-genai==1.0.9 \
    langchain-ollama==0.2.1 \
    lorem-text==2.1 \
    google-api-core==2.24.2 \
    pydantic==2.10.6 \
    pydantic-settings==2.7.1

COPY gcloud_logs_detect.py llmtest.py gcloud_logs_llmsummary.py gcloud_event_create.py ./

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python"]
CMD ["-m", "gcloud_logs_anomaly_detection", "--help"]
