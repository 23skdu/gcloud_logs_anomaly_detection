"""Longbow vector storage operations for log entries."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from gcloud_logs_anomaly_detection.config import LongbowConfig
from gcloud_logs_anomaly_detection.embeddings import embed_log_entries
from gcloud_logs_anomaly_detection.longbow_client import (
    ensure_dataset,
    search_by_id,
    search_filtered,
    search_hybrid,
    search_temporal,
    search_turboquant,
    search_vectors,
    store_vectors,
)

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger("gcloud_anomaly.longbow_store")


def store_log_entries(
    entries: list[dict[str, Any]],
    config: LongbowConfig | None = None,
) -> int:
    """Embed and store log entries in Longbow. Returns count stored."""
    if not entries:
        return 0
    if config is None:
        config = LongbowConfig()

    ensure_dataset(config)
    vectors = embed_log_entries(entries, model_name=config.embedding_model)

    metadata: list[dict[str, Any]] = []
    for entry in entries:
        ts = entry.get("timestamp")
        ts_nanos = 0
        if ts is not None:
            ts_nanos = int(ts.timestamp() * 1000000000.0) if isinstance(ts, datetime) else int(ts)
        metadata.append(
            {
                "timestamp": ts_nanos,
                "severity": str(entry.get("severity", "")),
                "resource": str(entry.get("resource", "")),
                "message": str(entry.get("message", "") or entry.get("payload", "")),
                "labels": str(entry.get("labels", "")),
            }
        )

    count = store_vectors(vectors, metadata, config)
    logger.info("Stored %d log entries in Longbow dataset '%s'", count, config.dataset)
    return count


def search_similar_logs(
    query: str,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> pd.DataFrame:
    """Semantic search: find logs similar to a text query."""
    from gcloud_logs_anomaly_detection.embeddings import embed_text

    if config is None:
        config = LongbowConfig()
    vector = embed_text(query, model_name=config.embedding_model)
    result = search_vectors(vector, k=k, config=config)
    if hasattr(result, "compute"):
        return result.compute()
    return result  # type: ignore[no-any-return]


def search_filtered_logs(
    query: str,
    filters: list[dict[str, Any]],
    k: int = 10,
    config: LongbowConfig | None = None,
) -> pd.DataFrame:
    """Filtered search: combine semantic similarity with metadata filters.

    Filters example: [{"field": "severity", "op": "eq", "value": "ERROR"}]
    Supports: eq, neq, gt, gte, lt, lte, in, like
    """
    from gcloud_logs_anomaly_detection.embeddings import embed_text

    if config is None:
        config = LongbowConfig()
    vector = embed_text(query, model_name=config.embedding_model)
    result = search_filtered(vector, filters=filters, k=k, config=config)
    if hasattr(result, "compute"):
        return result.compute()
    return result  # type: ignore[no-any-return]


def search_hybrid_logs(
    query: str,
    text_query: str | None = None,
    alpha: float = 0.7,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> pd.DataFrame:
    """Hybrid search: combine dense + sparse retrieval with RRF."""
    from gcloud_logs_anomaly_detection.embeddings import embed_text

    if config is None:
        config = LongbowConfig()
    vector = embed_text(query, model_name=config.embedding_model)
    result = search_hybrid(
        vector, text_query=text_query, alpha=alpha, k=k, config=config
    )
    if hasattr(result, "compute"):
        return result.compute()
    return result  # type: ignore[no-any-return]


def search_temporal_logs(
    search_type: str = "sliding_window_time",
    duration: str = "1h",
    k: int = 10,
    config: LongbowConfig | None = None,
) -> pd.DataFrame:
    """Temporal search: query logs within a time window."""
    if config is None:
        config = LongbowConfig()
    result = search_temporal(
        search_type=search_type, duration=duration, k=k, config=config
    )
    if hasattr(result, "compute"):
        return result.compute()
    return result  # type: ignore[no-any-return]


def search_logs_by_id(
    vector_id: int,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> pd.DataFrame:
    """Find logs similar to a known log entry by its Longbow ID."""
    if config is None:
        config = LongbowConfig()
    result = search_by_id(vector_id, k=k, config=config)
    if hasattr(result, "compute"):
        return result.compute()
    return result  # type: ignore[no-any-return]


def search_turboquant_logs(
    query: str,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> pd.DataFrame:
    """Search compressed TurboQuant vectors."""
    from gcloud_logs_anomaly_detection.embeddings import embed_text

    if config is None:
        config = LongbowConfig()
    vector = embed_text(query, model_name=config.embedding_model)
    result = search_turboquant(vector, k=k, config=config)
    if hasattr(result, "compute"):
        return result.compute()
    return result  # type: ignore[no-any-return]
