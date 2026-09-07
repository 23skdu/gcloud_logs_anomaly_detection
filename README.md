# gcloud-logs-anomaly-detection

Machine Learning tool to find anomalies in Google Cloud Logging events

## Features

- **Anomaly Detection**: Uses Isolation Forest ML algorithm to detect anomalies in log data
- **LLM Summarization**: Uses Google's Gemini LLM to summarize log entries
- **Test Data Generation**: Generate sample log events for testing
- **Unified CLI**: Single entry point for all commands via `gcloud-anomaly`
- **Structured Logging**: JSON-formatted logs with performance metrics
- **Error Handling**: Typed exception hierarchy with retry logic
- **Docker Support**: Multi-stage build, non-root user, healthcheck

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
| `LOG_FILTER` | Log filter query for LLM summarizer | `severity >= INFO` |
| `HOURS_AGO` | Hours of logs to fetch for summarizer | `1` |
| `INTERVAL_HOURS` | Hours between scheduled summarization runs | `1` |
| `NUMEVENTS` | Number of test events to generate | `1000` |
| `MODELNAME` | Ollama model for llmtest | `smollm2:135m` |

### Authentication

This tool uses Google Cloud Application Default Credentials (ADC). Set up authentication:

```bash
gcloud auth application-default login
```

Or set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your service account key file.

## Usage

### Unified CLI

```bash
gcloud-anomaly detect          # Detect anomalies
gcloud-anomaly summarize       # Summarize logs with LLM
gcloud-anomaly generate        # Generate test events
gcloud-anomaly ask "question"  # Ask local Ollama LLM
```

### Direct Script Execution

```bash
python gcloud_logs_detect.py       # Anomaly detection
python gcloud_logs_llmsummary.py   # LLM summarization
python gcloud_event_create.py      # Generate test events
python llmtest.py "What is Python?"  # Test local LLM
```

## Docker

Build and run with Docker:

```bash
docker build -t gcloud-logs-anomaly-detection .
docker run -it --rm \
  -v ~/.config/gcloud:/home/appuser/.config/gcloud \
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

### Pre-commit

```bash
pre-commit install
pre-commit run --all-files
```

## License

MIT
