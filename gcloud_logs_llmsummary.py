#!/usr/bin/env python3
"""LLM-powered log summarization for Google Cloud Logging."""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from google.api_core.exceptions import ClientError
from google.cloud import logging as gcp_logging

try:
    from langchain import LLMChain
    from langchain.chains import LLMChain
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.prompts import PromptTemplate
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import StrOutputParser
    from langchain_core.runnables import RunnablePassthrough

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

PROJECT_ID = os.environ.get("GCP_PROJECT", "")
LOG_FILTER = os.environ.get("LOG_FILTER", "severity >= INFO")
MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-2.0-flash-lite")
HOURS_AGO = int(os.environ.get("HOURS_AGO", "1"))
INTERVAL_HOURS = int(os.environ.get("INTERVAL_HOURS", "1"))


def timeit(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator for observability tracing."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logging.info("Function '%s' took %.4f seconds to execute.", func.__name__, end_time - start_time)
        return result

    return wrapper


@timeit
def get_log_entries(
    project_id: str,
    filter_query: str,
    hours_ago: int = 1,
) -> List[Dict[str, Any]]:
    """Fetch log entries from Google Cloud Logging."""
    if not project_id:
        raise ValueError("GCP_PROJECT environment variable is required")

    client = gcp_logging.Client(project=project_id)
    now = datetime.now()
    start_time = now - timedelta(hours=hours_ago)
    start_time_iso = start_time.isoformat() + "Z"

    entries = list(
        client.list_entries(
            filter_=f'{filter_query} AND timestamp>="{start_time_iso}"',
            order_by="timestamp desc",
        )
    )

    log_entries: List[Dict[str, Any]] = []
    for entry in entries:
        timestamp = None
        if hasattr(entry, "timestamp") and entry.timestamp:
            timestamp = entry.timestamp.replace(tzinfo=timezone.utc)

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
def summarize_logs(logs: List[Dict[str, Any]], llm: Any) -> str:
    """Summarize log entries using LLM."""
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

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100)
    texts = text_splitter.split_text(log_text)

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


def create_llm(model_name: str, temperature: float = 0.0) -> Any:
    """Create LLM instance using Google ADC (Application Default Credentials)."""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("langchain and langchain-google-genai are required for LLM summarization")

    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
    )


async def run_log_summarization(
    project_id: str,
    filter_query: str,
    model_name: str,
) -> None:
    """Run the log summarization process."""
    try:
        if not PROJECT_ID:
            raise ValueError("GCP_PROJECT environment variable is required")

        logs = get_log_entries(project_id, filter_query, hours_ago=HOURS_AGO)
        llm = create_llm(model_name)
        summary = summarize_logs(logs, llm)
        print("--- Log Summary ---")
        print(summary)
    except ClientError as e:
        logging.error("Google API Error: %s", e)
    except Exception as e:
        logging.error("An error occurred: %s", e)


async def scheduled_task(
    project_id: str,
    filter_query: str,
    model_name: str,
    interval_hours: int = 1,
) -> None:
    """Run log summarization on a schedule."""
    while True:
        await run_log_summarization(project_id, filter_query, model_name)
        await asyncio.sleep(interval_hours * 3600)


def main() -> None:
    """Main entry point."""
    if not PROJECT_ID:
        print("Error: Please set the GCP_PROJECT environment variable.")
        print("Note: This tool uses Application Default Credentials (ADC).")
        print("Run 'gcloud auth application-default login' to set up credentials.")
        exit(1)

    print(f"Starting log summarization for project: {PROJECT_ID}")
    asyncio.run(scheduled_task(PROJECT_ID, LOG_FILTER, MODEL_NAME, INTERVAL_HOURS))


if __name__ == "__main__":
    main()
