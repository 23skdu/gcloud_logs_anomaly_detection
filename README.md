# gcloud-logs-anomaly-detection

[![Lint Python](https://github.com/23skdu/gcloud_logs_anomaly_detection/actions/workflows/lint-python.yml/badge.svg)](https://github.com/23skdu/gcloud_logs_anomaly_detection/actions/workflows/lint-python.yml)
[![Lint Dockerfile](https://github.com/23skdu/gcloud_logs_anomaly_detection/actions/workflows/lint-docker.yml/badge.svg)](https://github.com/23skdu/gcloud_logs_anomaly_detection/actions/workflows/lint-docker.yml)
[![Lint Markdown](https://github.com/23skdu/gcloud_logs_anomaly_detection/actions/workflows/lint-markdown.yml/badge.svg)](https://github.com/23skdu/gcloud_logs_anomaly_detection/actions/workflows/lint-markdown.yml)
[![Docker Build and Publish](https://github.com/23skdu/gcloud_logs_anomaly_detection/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/23skdu/gcloud_logs_anomaly_detection/actions/workflows/docker-publish.yml)

Machine Learning tool to find anomalies in Google Cloud Logging events

## Features

- **Anomaly Detection**: Uses Isolation Forest ML algorithm to detect anomalies in log data
- **LLM Summarization**: Uses Google's Gemini LLM to summarize log entries
- **Test Data Generation**: Generate sample log events for testing

## Installation

```bash
pip install -r requirements.txt
```

For development:

```bash
pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your settings
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GCP_PROJECT` | GCP Project ID (required) | - |
| `LOG_NAME` | Log name to monitor | `loremipsumevents` |
| `MODEL_NAME` | LLM model for summarization | `gemini-2.0-flash-lite` |
| `NUMEVENTS` | Number of test events to generate | `1000` |
| `MODELNAME` | Ollama model for llmtest | `smollm2:135m` |

### Authentication

This tool uses Google Cloud Application Default Credentials (ADC). Set up authentication:

```bash
gcloud auth application-default login
```

Or set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your service account key file.

## Usage

### Anomaly Detection

Detect anomalies in your logs:

```bash
python gcloud_logs_detect.py
```

### Log Summarization

Summarize logs using LLM:

```bash
python gcloud_logs_llmsummary.py
```

### Generate Test Events

Generate sample log events:

```bash
python gcloud_event_create.py
```

### Test Local LLM

Test a local Ollama LLM:

```bash
python llmtest.py "What is Python?"
```

## Docker

Build and run with Docker:

```bash
docker build -t gcloud-logs-anomaly-detection .
docker run -it --rm \
  -v ~/.config/gcloud:/root/.config/gcloud \
  -e GCP_PROJECT=your-project \
  gcloud-logs-anomaly-detection
```

## Development

### Running Tests

```bash
pytest
```

### Linting

```bash
ruff check .
mypy .
```

## License

MIT
