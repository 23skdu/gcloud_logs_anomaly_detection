#!/usr/bin/env python3
"""LLM-powered log summarization for Google Cloud Logging."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from google.api_core.exceptions import ClientError
from google.cloud import logging as gcp_logging

from gcloud_logs_anomaly_detection.exceptions import (
    GCPAPIError,
    GCPConfigError,
    LLMSummarizationError,
)
from gcloud_logs_anomaly_detection.observability import (
    log_metric,
    setup_logging,
    timeit,
)

try:
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

logger = logging.getLogger("gcloud_anomaly.llm")

PROJECT_ID = os.environ.get("GCP_PROJECT", "")
LOG_FILTER = os.environ.get("LOG_FILTER", "severity >= INFO")
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-2.0-flash-lite")
HOURS_AGO = int(os.environ.get("HOURS_AGO", "1"))
INTERVAL_HOURS = int(os.environ.get("INTERVAL_HOURS", "1"))


@timeit
def get_log_entries(
    project_id: str,
    filter_query: str,
    hours_ago: int = 1,
    max_retries: int = 3,
) -> list[dict[str, Any]]:
    """Fetch log entries from Google Cloud Logging with retry logic.

    Raises:
        GCPConfigError: If project_id is not provided.
        GCPAPIError: If all retry attempts fail.
    """
    if not project_id:
        raise GCPConfigError(
            "GCP_PROJECT environment variable is required. "
            "Run 'gcloud auth application-default login' to set up credentials."
        )

    client = gcp_logging.Client(project=project_id)
    now = datetime.now()
    start_time = now - timedelta(hours=hours_ago)
    start_time_iso = start_time.isoformat() + "Z"

    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            entries = list(
                client.list_entries(
                    filter_=f'{filter_query} AND timestamp>="{start_time_iso}"',
                    order_by="timestamp desc",
                )
            )
            log_metric("log_entries_fetched", len(entries))
            break
        except ClientError as exc:
            last_exc = exc
            logger.warning("Attempt %d/%d failed: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    else:
        raise GCPAPIError(
            f"Failed to fetch logs after {max_retries} attempts", cause=last_exc
        )

    log_entries: list[dict[str, Any]] = []
    for entry in entries:
        timestamp = None
        if hasattr(entry, "timestamp") and entry.timestamp:
            timestamp = entry.timestamp.replace(tzinfo=UTC)

        log_entries.append(
            {
                "timestamp": timestamp,
                "severity": entry.severity,
                "message": entry.payload if hasattr(entry, "payload") else entry.message,
                "resource": entry.resource,
                "labels": entry.labels,
            }
        )
    return log_entries


@timeit
def summarize_logs(logs: list[dict[str, Any]], llm: Any) -> str:
    """Summarize log entries using LLM.

    Raises:
        LLMSummarizationError: If summarization fails.
    """
    if not logs:
        return "No log entries to summarize."

    log_text = "\n\n".join(
        f"Timestamp: {log['timestamp'].isoformat()} \n"
        f"Severity: {log['severity']}\n"
        f"Message: {log['message']}\n"
        f"Resource: {log['resource']}\n"
        f"Labels: {log['labels']}"
        for log in logs
    )

    if not LANGCHAIN_AVAILABLE:
        raise LLMSummarizationError(
            "langchain and langchain-google-genai are required for LLM summarization"
        )

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100)
    texts = text_splitter.split_text(log_text)
    log_metric("text_chunks", len(texts))

    prompt_template = """
    You are a senior engineer that understands logs and can summarize the logs.
    Summarize the following logs in concise bullet points.
    The logs:
    {logs}
    Summary:
    """
    prompt = PromptTemplate.from_template(prompt_template)
    summary = ""

    for chunk in texts:
        chain = (
            {"logs": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        summary += chain.invoke({"logs": chunk}, config={"tags": ["summarization"]})

    return summary


def create_llm(
    model_name: str,
    temperature: float = 0.0,
    backend: str = "gemini",
) -> Any:
    """Create LLM instance for the specified backend.

    Backends:
        gemini  - Google Gemini via langchain-google-genai (default)
        quarrel - Longbow-Quarrel local inference (OpenAI-compatible)
        ollama  - Local Ollama via langchain-ollama
    """
    if backend == "quarrel":
        from gcloud_logs_anomaly_detection.quarrel_llm import create_quarrel_llm

        return create_quarrel_llm()

    if backend == "ollama":
        try:
            from langchain_ollama import OllamaLLM
        except ImportError as exc:
            raise ImportError("langchain-ollama is required for ollama backend") from exc
        return OllamaLLM(model=model_name)

    # Default: gemini
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("langchain and langchain-google-genai are required")
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
    )


BACKEND = os.environ.get("LLM_BACKEND", "gemini")


async def run_log_summarization(
    project_id: str,
    filter_query: str,
    model_name: str,
) -> None:
    """Run the log summarization process."""
    if not PROJECT_ID:
        raise GCPConfigError("GCP_PROJECT environment variable is required")

    logs = get_log_entries(project_id, filter_query, hours_ago=HOURS_AGO)
    llm = create_llm(model_name, backend=BACKEND)
    summary = summarize_logs(logs, llm)
    print("--- Log Summary ---")
    print(summary)


async def scheduled_task(
    project_id: str,
    filter_query: str,
    model_name: str,
    interval_hours: int = 1,
) -> None:
    """Run log summarization on a schedule."""
    while True:
        try:
            await run_log_summarization(project_id, filter_query, model_name)
        except Exception as exc:
            logger.error("Scheduled task failed: %s", exc)
        await asyncio.sleep(interval_hours * 3600)


def main() -> None:
    """Main entry point."""
    setup_logging()

    if not PROJECT_ID:
        print("Error: Please set the GCP_PROJECT environment variable.")
        print("Note: This tool uses Application Default Credentials (ADC).")
        print("Run 'gcloud auth application-default login' to set up credentials.")
        exit(1)

    print(f"Starting log summarization for project: {PROJECT_ID} (backend: {BACKEND})")
    asyncio.run(scheduled_task(PROJECT_ID, LOG_FILTER, MODEL_NAME, INTERVAL_HOURS))


if __name__ == "__main__":
    main()
