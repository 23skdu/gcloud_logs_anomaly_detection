# Standalone Scripts Reference

All standalone execution scripts are located in the [`scripts/`](../scripts) directory. Each script can be executed directly with Python or via the unified `gcloud-anomaly` CLI.

## Quick Reference

| Script | Purpose | CLI Equivalent | Key Configuration |
|--------|---------|----------------|-------------------|
| [`gcloud_logs_detect.py`](../scripts/gcloud_logs_detect.py) | Isolation Forest anomaly detection in GCP logs | `gcloud-anomaly detect` | `LOG_NAME`, `LOG_PAGE_SIZE`, `LOG_CONTAMINATION` |
| [`gcloud_logs_llmsummary.py`](../scripts/gcloud_logs_llmsummary.py) | LLM-powered log summarization | `gcloud-anomaly summarize` | `GCP_PROJECT`, `MODEL_NAME`, `LLM_BACKEND` |
| [`gcloud_event_create.py`](../scripts/gcloud_event_create.py) | Synthetic test event generator for GCP Logging | `gcloud-anomaly generate` | `NUMEVENTS`, `LOG_NAME` |
| [`llmtest.py`](../scripts/llmtest.py) | Local Ollama LLM integration tester | `gcloud-anomaly ask` | `MODELNAME` |

---

## Authentication

All scripts connecting to Google Cloud use **Application Default Credentials (ADC)**:

```bash
gcloud auth application-default login
```

Alternatively, set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`.

---

## 1. Anomaly Detection (`scripts/gcloud_logs_detect.py`)

Fetches recent logs from Google Cloud Logging, preprocesses features (timestamp, severity level, message length), trains an **Isolation Forest** unsupervised ML model, and visualizes anomalies.

### Execution

```bash
# Direct script execution
python scripts/gcloud_logs_detect.py

# Via unified CLI
gcloud-anomaly detect --log-name loremipsumevents --contamination auto

# Detect and automatically store anomalous vectors into Longbow
gcloud-anomaly detect --store-vector
```

### Configuration Options

| Variable | CLI Option | Description | Default |
|----------|------------|-------------|---------|
| `LOG_NAME` | `--log-name` | Log name to analyze | `loremipsumevents` |
| `LOG_PAGE_SIZE` | `--page-size` | Number of log entries to fetch | `10000` |
| `LOG_CONTAMINATION` | `--contamination` | Contamination parameter (`auto` or float `0.0`-`0.5`) | `auto` |
| `LOG_RANDOM_STATE` | - | Random seed for Isolation Forest reproducibility | `42` |
| `STORE_VECTOR` | `--store-vector` | Store detected anomalies as vectors in Longbow | `0` |

### Output

- **Console**: Summary count of detected anomalies versus normal entries.
- **Artifact**: `anomaly_detection.png` scatter plot visualizing anomalies across entry index and message length.
- **Observability**: Structured JSON logs with execution time and anomaly metrics.

---

## 2. LLM Summarizer (`scripts/gcloud_logs_llmsummary.py`)

Fetches recent log entries within a configurable time window and uses a Large Language Model to synthesize an operational summary. Supports **Google Gemini**, **Longbow-Quarrel**, and **Ollama**.

### Execution

```bash
# Direct script execution
python scripts/gcloud_logs_llmsummary.py

# Via unified CLI (Gemini)
gcloud-anomaly summarize --project-id my-project --hours-ago 1

# Summarize using local Quarrel inference
gcloud-anomaly summarize --project-id my-project --backend quarrel

# Summarize using local Ollama
gcloud-anomaly summarize --project-id my-project --backend ollama
```

### Configuration Options

| Variable | CLI Option | Description | Default |
|----------|------------|-------------|---------|
| `GCP_PROJECT` | `--project-id` | Google Cloud Project ID (required) | - |
| `LLM_BACKEND` | `--backend` | Inference backend (`gemini`, `quarrel`, `ollama`) | `gemini` |
| `MODEL_NAME` | `--model-name` | Model name for summarization | `gemini-2.0-flash-lite` |
| `LOG_FILTER` | - | GCP Logging filter expression | `severity >= INFO` |
| `HOURS_AGO` | `--hours-ago` | Lookback window in hours | `1` |
| `INTERVAL_HOURS` | - | Interval between scheduled runs | `1` |

---

## 3. Test Event Generator (`scripts/gcloud_event_create.py`)

Generates synthetic log events with varying severities and lorem ipsum payloads, transmitting them directly to Google Cloud Logging for pipeline testing and ML validation.

### Execution

```bash
# Direct script execution
python scripts/gcloud_event_create.py

# Via unified CLI
gcloud-anomaly generate --num-events 500 --log-name loremipsumevents
```

### Configuration Options

| Variable | CLI Option | Description | Default |
|----------|------------|-------------|---------|
| `NUMEVENTS` | `--num-events` | Number of events to generate | `1000` |
| `LOG_NAME` | `--log-name` | Destination GCP log name | `loremipsumevents` |

---

## 4. Local LLM Tester (`scripts/llmtest.py`)

Utility script for verifying local LLM connectivity and prompt execution against an Ollama instance.

### Execution

```bash
# Direct script execution
python scripts/llmtest.py "Explain anomaly detection in log files"

# Via unified CLI
gcloud-anomaly ask "Explain anomaly detection in log files" --model smollm2:135m
```

### Configuration Options

| Variable | CLI Option | Description | Default |
|----------|------------|-------------|---------|
| `MODELNAME` | `--model` | Ollama model identifier | `smollm2:135m` |
| `OLLAMA_HOST` | - | Host endpoint for Ollama API | `http://localhost:11434` |

---

## How the Scripts Work Together

The scripts form a small pipeline around Google Cloud Logging, an optional vector
store (Longbow), and local/remote LLM backends. They share configuration through
environment variables (see `.env.example`) and the unified `gcloud-anomaly` CLI
in `gcloud_logs_anomaly_detection/cli.py`.

```text
gcloud_event_create.py  ──►  GCP Logging  ──►  gcloud_logs_detect.py
        (generate test data)                          (Isolation Forest)
                                                          │
                                                          ▼
                                              Longbow vector store (optional)
                                                          │
                          ┌───────────────────────────────┼───────────────────────────────┐
                          ▼                               ▼                               ▼
                gcloud_logs_llmsummary.py            longbow_store.py                 llmtest.py
                (Gemini / Quarrel / Ollama)           (ingest + search)               (Ollama smoke test)
```

### Typical end-to-end flow

1. **Generate data** (optional, for testing):

   ```bash
   gcloud-anomaly generate --num-events 1000
   ```

   runs `scripts/gcloud_event_create.py`, which writes synthetic entries to GCP
   Logging under `LOG_NAME`.

2. **Detect anomalies**:

   ```bash
   gcloud-anomaly detect
   # or store results as vectors
   gcloud-anomaly detect --store-vector
   ```

   runs `scripts/gcloud_logs_detect.py`. With `STORE_VECTOR=1` /
   `--store-vector` it calls `longbow_store.store_log_entries` to persist
   anomalous entries.

3. **Ingest logs for semantic search** (independent of detection):

   ```bash
   gcloud-anomaly ingest --hours-ago 24
   ```

   uses `scripts/gcloud_logs_llmsummary.get_log_entries` to fetch entries and
   `longbow_store` to embed and store them. Supports `--incremental`
   (watermark) and `--async` (batched) modes.

4. **Search**:

   ```bash
   gcloud-anomaly search "authentication failures"
   ```

   queries Longbow via `longbow_store` / `longbow_client`.

5. **Summarize**:

   ```bash
   gcloud-anomaly summarize --backend gemini
   ```

   runs `scripts/gcloud_logs_llmsummary.py`, fetching logs and producing a
   bullet-point summary through the selected LLM backend. Backends are
   discovered via `gcloud_logs_anomaly_detection.config` (`discover_llm_backends`).

6. **Smoke-test a local LLM**:

   ```bash
   gcloud-anomaly ask "What is Python?"
   ```

   runs `scripts/llmtest.py` against Ollama.

### Shared infrastructure

- `gcloud_logs_anomaly_detection/config.py` holds the pydantic-settings classes
  (`DetectConfig`, `LLMConfig`, `EventCreateConfig`, `LLMTestConfig`,
  `LongbowConfig`, `QuarrelConfig`) used across scripts and the CLI.
- `scripts/config.py` re-exports them for direct script usage.
- `gcloud_logs_anomaly_detection/observability.py` provides `setup_logging`,
  `timeit`, and `log_metric` used by every script.
- `gcloud_logs_anomaly_detection/exceptions.py` provides the typed exception
  hierarchy (`GCPAPIError`, `LLMSummarizationError`, ...).

### Running scripts directly

Each script bootstraps `sys.path` so it can be run from the repository root:

```bash
python scripts/gcloud_logs_detect.py
python scripts/gcloud_logs_llmsummary.py
python scripts/gcloud_event_create.py
python scripts/llmtest.py "What is Python?"
```

When run directly, scripts read their settings from environment variables (or
`.env`). The unified CLI sets these variables for you.

### Virtual environment

A single virtual environment (`.venv`) is used for development and CI. Create it
with `python3 -m venv .venv` (or `uv venv .venv`) and install with
`pip install -e ".[dev]"`. The Makefile's `PYTHON` variable prefers
`.venv/bin/python` when present.
