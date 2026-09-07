# Google Cloud Log Event Generator

This script (`gcloud_event_create.py`) generates synthetic log events and sends
them to Google Cloud Logging.

## Features

- Uses lorem-text to generate random log messages.
- Sends logs to a specified Google Cloud Logging log name.
- Configurable number of events via environment variables.
- Structured JSON logging with `@timeit` decorator and metric emission.
- Error handling via `GCPAPIError` exception.

## Usage

```bash
python gcloud_event_create.py
```

Or via the unified CLI:

```bash
gcloud-anomaly generate --num-events 500
```

## Authentication

Uses Google Cloud Application Default Credentials (ADC):

```bash
gcloud auth application-default login
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `NUMEVENTS` | Number of events to generate | `1000` |
| `LOG_NAME` | Name of the log to write to | `loremipsumevents` |
