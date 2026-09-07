FROM python:3.14-slim
LABEL author=23skdu@users.noreply.github.com

WORKDIR /app

RUN apt-get update && apt-get -y upgrade && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    tzdata==2025.2 \
    pandas==3.0.5 \
    scikit-learn==1.9.0 \
    google-cloud-logging==3.16.3 \
    seaborn==0.13.2 \
    matplotlib==3.11.1 \
    langchain==1.3.18 \
    langchain-google-genai==4.3.7 \
    langchain-ollama==1.1.0 \
    lorem-text==3.0 \
    google-api-core==2.34.0 \
    pydantic==2.13.5 \
    pydantic-settings==2.15.0

COPY config.py gcloud_logs_detect.py llmtest.py gcloud_logs_llmsummary.py gcloud_event_create.py ./

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python"]
CMD ["gcloud_logs_detect.py", "--help"]
