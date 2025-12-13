FROM python:3.13-slim
LABEL author=23skdu@users.noreply.github.com

WORKDIR /app

RUN apt-get update && apt-get -y upgrade && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir tzdata==2025.2 pandas==2.3.3 scikit-learn==1.8.0 google-cloud-logging==3.12.1 seaborn==0.13.2

COPY gcloud_logs_detect.py llmtest.py gcloud_logs_llmsummary.py gcloud_event_create.py ./

CMD ["python", "-c", "print('works')"]
