#!/usr/bin/env python3
import os,time,asyncio,datetime
from typing import Callable, Any, Dict, List, Optional
from functools import wraps
from google.cloud import logging as gcp_logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from google.api_core.exceptions import ClientError # for error handling
from langchain.schema import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

PROJECT_ID = os.environ.get("GCP_PROJECT")
LOG_FILTER = "severity >= INFO"
MODEL_NAME = os.environ.get("MODEL_NAME","gemini-2.0-flash-lite")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# --- Decorator for observability tracing ---
def timeit(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Function '{func.__name__}' took {execution_time:.4f} seconds to execute.")
        return result
    return wrapper

@timeit
def get_log_entries(
    project_id: str, filter_query: str, hours_ago: int = 1
) -> List[Dict]:
    client = gcp_logging.Client(project=project_id)
    now = datetime.datetime.now()
    start_time = now - datetime.timedelta(hours=hours_ago)
    # Format start_time to ISO 8601 with Z (UTC)
    start_time_iso = start_time.isoformat() + "Z"
    entries = list(
        client.list_entries(
            filter_=f'{filter_query} AND timestamp>="{start_time_iso}"',
            order_by="timestamp desc",
        )
    )
    log_entries = []
    for entry in entries:
        # Ensure 'timestamp' is timezone-aware
        if hasattr(entry, 'timestamp') and entry.timestamp:
            timestamp = entry.timestamp.replace(tzinfo=datetime.timezone.utc)
        else:
            timestamp = None # or handle the missing timestamp case appropriately
        log_entries.append(
            {
                "timestamp": timestamp,  # Store the timezone-aware timestamp
                "severity": entry.severity,
                "message": entry.payload if hasattr(entry, 'payload') else entry.message,
                "resource": entry.resource,
                "labels": entry.labels,
            }
        )
    return log_entries

@timeit
def summarize_logs(logs: List[Dict], llm: ChatGoogleGenerativeAI) -> str:
    if not logs:
        return "No log entries to summarize."
    log_text = "\n\n".join(
        [f"Timestamp: {log['timestamp'].isoformat()} \nSeverity: {log['severity']}\nMessage: {log['message']}\nResource: {log['resource']}\nLabels: {log['labels']}" for log in logs]
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

@timeit
async def run_log_summarization(project_id: str, filter_query: str, model_name: str) -> None:
    try:
        logs = get_log_entries(project_id, filter_query, hours_ago=1)
        llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=GOOGLE_API_KEY, temperature=0)
        summary = summarize_logs(logs, llm)
        print("--- Log Summary ---")
        print(summary)
    except ClientError as e:
        print(f"Google API Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

async def scheduled_task(project_id: str, filter_query: str, model_name: str, interval_hours: int = 1) -> None:
    while True:
        await run_log_summarization(project_id, filter_query, model_name)
        await asyncio.sleep(interval_hours * 3600)  

if __name__ == "__main__":
    if not PROJECT_ID:
        print("Error: Please set the GCP_PROJECT environment variable.")
        exit(1)
    print(f"Starting log summarization for project: {PROJECT_ID}")
    asyncio.run(scheduled_task(PROJECT_ID, LOG_FILTER, MODEL_NAME))
