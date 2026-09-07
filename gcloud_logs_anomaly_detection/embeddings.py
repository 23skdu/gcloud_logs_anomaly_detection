"""Embedding utilities for log entries."""

from __future__ import annotations

from typing import Any

from gcloud_logs_anomaly_detection.observability import log_metric, timeit

_model: Any = None


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
    return f"{severity} {message} {resource} {labels}"
