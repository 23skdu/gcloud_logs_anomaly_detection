# gcloud-logs-anomaly-detection

Machine Learning tool to find anomalies in Google Cloud Logging events

## Features

- **Anomaly Detection**: Uses Isolation Forest ML algorithm to detect anomalies in log data
- **LLM Summarization**: Uses Google's Gemini LLM to summarize log entries (with Quarrel/Ollama backends)
- **Vector Storage**: Store and search log entries via Longbow vector database
- **Semantic Search**: Dense, sparse, hybrid, filtered, temporal, and TurboQuant search modes
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
| `LLM_BACKEND` | LLM backend (`gemini`/`quarrel`/`ollama`) | `gemini` |
| `LONGBOW_URI` | Longbow data port URI | `grpc://localhost:3000` |
| `LONGBOW_META_URI` | Longbow meta port URI | `grpc://localhost:3001` |
| `LONGBOW_DATASET` | Longbow dataset name | `gcloud_logs` |
| `LONGBOW_DIMS` | Embedding dimensions | `384` |
| `LONGBOW_DATA_TYPE` | Vector data type | `float32` |
| `LONGBOW_SEARCH_K` | Default search results | `10` |
| `LONGBOW_SEARCH_ALPHA` | Hybrid blending weight | `0.7` |
| `LONGBOW_EMBEDDING_MODEL` | Sentence-transformers model | `all-MiniLM-L6-v2` |
| `QUARREL_BASE_URL` | Quarrel API base URL | `http://localhost:8080` |
| `QUARREL_API_KEY` | Quarrel API key | (empty) |
| `QUARREL_MODEL` | Quarrel model name | `default` |
| `QUARREL_TEMPERATURE` | LLM temperature | `0.0` |
| `QUARREL_MAX_TOKENS` | Max generation tokens | `4096` |

### Authentication

This tool uses Google Cloud Application Default Credentials (ADC). Set up authentication:

```bash
gcloud auth application-default login
```

Or set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your service account key file.

## Usage

### Unified CLI

```bash
gcloud-anomaly detect                    # Detect anomalies
gcloud-anomaly detect --store-vector     # Detect and store in Longbow
gcloud-anomaly summarize                 # Summarize logs with LLM (Gemini)
gcloud-anomaly summarize --backend quarrel  # Summarize with Quarrel
gcloud-anomaly summarize --backend ollama   # Summarize with Ollama
gcloud-anomaly generate                  # Generate test events
gcloud-anomaly ask "question"            # Ask local Ollama LLM
gcloud-anomaly search "query"            # Semantic search in Longbow
gcloud-anomaly ingest                    # Ingest GCP logs into Longbow
```

### Vector Search (Longbow)

```bash
# Dense semantic search
gcloud-anomaly search "authentication failures"

# Filtered search
gcloud-anomaly search "errors" --mode filtered --filter severity=eq:ERROR

# Hybrid search (dense + sparse)
gcloud-anomaly search "timeout" --mode hybrid --alpha 0.7

# Temporal search
gcloud-anomaly search --mode temporal --duration 1h

# Search by vector ID
gcloud-anomaly search --mode by-id --id 12345

# Compressed TurboQuant search
gcloud-anomaly search "disk full" --mode turboquant

# Ingest logs from GCP
gcloud-anomaly ingest --log-name compute --hours-ago 24
gcloud-anomaly ingest --filter "severity >= ERROR" --hours-ago 72
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

### Docker Compose with Longbow

```bash
# Start Longbow vector storage
docker compose -f docker-compose.longbow.yml up longbow

# Start Quarrel inference engine
docker compose -f docker-compose.longbow.yml up quarrel

# Start all services
docker compose -f docker-compose.longbow.yml --profile full up
```

## Architecture

```
gcloud-anomaly (CLI)
├── detect        → gcloud_logs_detect.py (Isolation Forest)
├── summarize     → gcloud_logs_llmsummary.py (Gemini/Quarrel/Ollama)
├── search        → longbow_store.py → longbow_client.py → Longbow
├── ingest        → gcloud_logs_llmsummary.py → longbow_store.py
├── generate      → gcloud_event_create.py
└── ask           → llmtest.py (Ollama)
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
