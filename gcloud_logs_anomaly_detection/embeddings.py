"""Embedding utilities for log entries."""

from __future__ import annotations

import json
import logging
from typing import Any, TypedDict

from gcloud_logs_anomaly_detection.observability import log_metric, timeit

logger = logging.getLogger("gcloud_anomaly.embeddings")
_model: Any = None


# --- Log Entry Schema Normalization (Improvement #7) ---


class LogEntrySchema(TypedDict, total=False):
    """Normalized log entry schema across GCP log types."""

    timestamp: Any
    severity: str
    message: str
    resource: str
    labels: dict[str, Any]
    log_name: str
    insert_id: str


_LOG_TYPE_MAPPERS: dict[str, dict[str, str]] = {
    "audit": {
        "message": "protoPayload.statusMessage",
        "severity": "severity",
        "resource": "resource.labels.project_id",
        "resource_type": "resource.type",
    },
    "vpc_flow": {
        "message": "jsonPayload.connection",
        "severity": "severity",
        "resource": "resource.labels.vpc_network",
    },
    "app_engine": {
        "message": "textPayload",
        "severity": "severity",
        "resource": "resource.labels.module_id",
    },
    "cloud_run": {
        "message": "textPayload",
        "severity": "severity",
        "resource": "resource.labels.service_name",
    },
    "generic": {
        "message": "message",
        "severity": "severity",
        "resource": "resource",
    },
}


def _resolve_nested(data: dict[str, Any], path: str) -> Any:
    """Resolve a dotted path in a nested dict."""
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def normalize_entry(
    raw_entry: dict[str, Any],
    log_type: str = "generic",
) -> LogEntrySchema:
    """Normalize a raw GCP log entry to the standard schema.

    Args:
        raw_entry: Raw log entry dict from GCP Logging API.
        log_type: Type of log (audit, vpc_flow, app_engine, cloud_run, generic).

    Returns:
        Normalized LogEntrySchema dict.
    """
    mapper = _LOG_TYPE_MAPPERS.get(log_type, _LOG_TYPE_MAPPERS["generic"])

    severity = _resolve_nested(raw_entry, mapper.get("severity", "severity")) or ""
    message = _resolve_nested(raw_entry, mapper.get("message", "message")) or ""
    resource = _resolve_nested(raw_entry, mapper.get("resource", "resource")) or ""

    if not message:
        message = raw_entry.get("message", "") or raw_entry.get("payload", "")

    labels = raw_entry.get("labels", {})
    if isinstance(labels, str):
        try:
            labels = json.loads(labels) if labels else {}
        except (json.JSONDecodeError, TypeError):
            labels = {"raw": labels}

    return LogEntrySchema(
        timestamp=raw_entry.get("timestamp"),
        severity=str(severity),
        message=str(message),
        resource=str(resource),
        labels=labels if isinstance(labels, dict) else {"raw": labels},
        log_name=raw_entry.get("log_name", ""),
        insert_id=raw_entry.get("insert_id", ""),
    )


def normalize_entries(
    entries: list[dict[str, Any]],
    log_type: str = "generic",
) -> list[LogEntrySchema]:
    """Normalize a batch of raw log entries."""
    return [normalize_entry(e, log_type) for e in entries]


def get_model(model_name: str = "all-MiniLM-L6-v2") -> Any:
    """Load and cache a sentence-transformers model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(model_name)
    return _model


@timeit
def embed_text(text: str, model_name: str = "all-MiniLM-L6-v2") -> list[float]:
    """Embed a single text string."""
    model = get_model(model_name)
    return model.encode(text).tolist()


@timeit
def embed_log_entry(
    entry: dict[str, Any], model_name: str = "all-MiniLM-L6-v2"
) -> list[float]:
    """Embed a single log entry dict into a vector."""
    text = _entry_to_text(entry)
    return embed_text(text, model_name)


@timeit
def embed_log_entries(
    entries: list[dict[str, Any]], model_name: str = "all-MiniLM-L6-v2"
) -> list[list[float]]:
    """Embed a batch of log entry dicts into vectors."""
    if not entries:
        return []
    texts = [_entry_to_text(e) for e in entries]
    model = get_model(model_name)
    vectors = model.encode(texts).tolist()
    log_metric("entries_embedded", len(vectors))
    return vectors


def _entry_to_text(entry: dict[str, Any]) -> str:
    """Convert a log entry dict to a text representation for embedding."""
    severity = entry.get("severity", "")
    message = entry.get("message", "") or entry.get("payload", "")
    resource = entry.get("resource", "")
    labels = entry.get("labels", "")
    if isinstance(labels, dict):
        labels = " ".join(f"{k}={v}" for k, v in labels.items())
    return f"{severity} {message} {resource} {labels}"
