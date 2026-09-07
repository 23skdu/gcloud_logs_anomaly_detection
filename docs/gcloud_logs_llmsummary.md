# Google Cloud Logs LLM Summarizer

This script (`gcloud_logs_llmsummary.py`) fetches recent logs and uses a Large
Language Model (LLM) to generate a concise summary.

## Features

- Fetches logs from the last hour (configurable).
- Uses **LangChain** and **Google Gemini** (via ChatGoogleGenerativeAI) for summarization.
- Structured JSON logging with `@timeit` decorator and metric emission.
- Runs as a scheduled task (asyncio loop) with configurable interval.
- Retry logic with exponential backoff for transient GCP API errors.
- Typed exception hierarchy (`GCPConfigError`, `GCPAPIError`, `LLMSummarizationError`).

## Usage

```bash
python gcloud_logs_llmsummary.py
```

Or via the unified CLI:

```bash
gcloud-anomaly summarize
```

## Authentication

Uses Google Cloud Application Default Credentials (ADC):

```bash
gcloud auth application-default login
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `GCP_PROJECT` | Google Cloud Project ID (required) | - |
| `MODEL_NAME` | LLM model name | `gemini-2.0-flash-lite` |
| `LOG_FILTER` | Log filter query | `severity >= INFO` |
| `HOURS_AGO` | Hours of logs to fetch | `1` |
| `INTERVAL_HOURS` | Hours between scheduled runs | `1` |
