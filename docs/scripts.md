# Standalone Scripts Reference

All standalone execution scripts are located in the [`scripts/`](file:///home/rsd/REPOS/gcloud_logs_anomaly_detection/scripts) directory. Each script can be executed directly with Python or via the unified `gcloud-anomaly` CLI.

## Quick Reference

| Script | Purpose | CLI Equivalent | Key Configuration |
|--------|---------|----------------|-------------------|
| [`gcloud_logs_detect.py`](file:///home/rsd/REPOS/gcloud_logs_anomaly_detection/scripts/gcloud_logs_detect.py) | Isolation Forest anomaly detection in GCP logs | `gcloud-anomaly detect` | `LOG_NAME`, `LOG_PAGE_SIZE`, `LOG_CONTAMINATION` |
| [`gcloud_logs_llmsummary.py`](file:///home/rsd/REPOS/gcloud_logs_anomaly_detection/scripts/gcloud_logs_llmsummary.py) | LLM-powered log summarization | `gcloud-anomaly summarize` | `GCP_PROJECT`, `MODEL_NAME`, `LLM_BACKEND` |
| [`gcloud_event_create.py`](file:///home/rsd/REPOS/gcloud_logs_anomaly_detection/scripts/gcloud_event_create.py) | Synthetic test event generator for GCP Logging | `gcloud-anomaly generate` | `NUMEVENTS`, `LOG_NAME` |
| [`llmtest.py`](file:///home/rsd/REPOS/gcloud_logs_anomaly_detection/scripts/llmtest.py) | Local Ollama LLM integration tester | `gcloud-anomaly ask` | `MODELNAME` |

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
