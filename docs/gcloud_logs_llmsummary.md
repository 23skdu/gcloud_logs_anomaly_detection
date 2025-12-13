# Google Cloud Logs LLM Summarizer

This script (gcloud_logs_llmsummary.py) fetches recent logs and uses a Large
Language Model (LLM) to generate a concise summary.

## Features

- Fetches logs from the last hour.
- Uses **LangChain** and **Google Gemini** (via ChatGoogleGenerativeAI) for summarization.
- Includes a custom @timeit decorator for performance observability.
- Runs as a scheduled task (asyncio loop).

## Configuration

- GCP_PROJECT: Google Cloud Project ID (Required).
- GOOGLE_API_KEY: API Key for Google Gemini.
- MODEL_NAME: LLM model name (default: 'gemini-2.0-flash-lite').
