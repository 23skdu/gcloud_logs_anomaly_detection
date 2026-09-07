# Google Cloud Logs Anomaly Detection

This script (`gcloud_logs_detect.py`) fetches logs from Google Cloud, analyzes
them for anomalies using Machine Learning, and visualizes the results.

## Features

- Fetches logs using the Google Cloud Logging API.
- Preprocesses data: maps severity levels to integers, calculates message length.
- Uses **Isolation Forest** (scikit-learn) to detect anomalies based on
  timestamp, severity, and message length.
- Generates a scatter plot (`anomaly_detection.png`) visualizing anomalies.
- Structured JSON logging with performance metrics via `@timeit` decorator.
- Typed exception hierarchy (`GCPAPIError`, `AnomalyDetectionError`).

## Usage

```bash
python gcloud_logs_detect.py
```

Or via the unified CLI:

```bash
gcloud-anomaly detect
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_NAME` | Name of the log to analyze | `loremipsumevents` |
| `LOG_PAGE_SIZE` | Number of log entries to fetch | `10000` |
| `LOG_CONTAMINATION` | Contamination parameter for IsolationForest | `auto` |
| `LOG_RANDOM_STATE` | Random seed for reproducibility | `42` |

## Output

- Console: summary of anomalies detected vs total entries.
- File: `anomaly_detection.png` scatter plot.
- Logs: structured JSON with timing and metric data.
