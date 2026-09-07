"""Longbow vector storage operations for log entries."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from gcloud_logs_anomaly_detection.config import LongbowConfig
from gcloud_logs_anomaly_detection.embeddings import embed_log_entries, embed_text
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

logger = logging.getLogger("gcloud_anomaly.longbow_store")


# --- Structured Search Response (Improvement #6) ---


@dataclass
class LogEntry:
    """Normalized log entry in search results."""

    id: int
    score: float
    timestamp: str
    severity: str
    message: str
    resource: str
    labels: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Structured search result container."""

    entries: list[LogEntry]
    total: int
    query_time_ms: float
    mode: str
    query: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)

    def to_csv(self) -> str:
        if not self.entries:
            return ""
        headers = "id,score,timestamp,severity,message,resource,labels"
        rows = [
            f"{e.id},{e.score},{e.timestamp},{e.severity},{e.message},{e.resource},{json.dumps(e.labels, default=str)}"
            for e in self.entries
        ]
        return headers + "\n" + "\n".join(rows)


def _df_to_search_result(
    df: Any,
    mode: str,
    query: str,
    query_time_ms: float,
) -> SearchResult:
    """Convert a DataFrame to a structured SearchResult."""
    entries: list[LogEntry] = []
    for _, row in df.iterrows():
        entries.append(
            LogEntry(
                id=int(row.get("id", 0)),
                score=float(row.get("score", 0.0)),
                timestamp=str(row.get("timestamp", "")),
                severity=str(row.get("severity", "")),
                message=str(row.get("message", "")),
                resource=str(row.get("resource", "")),
                labels={},
            )
        )
    return SearchResult(
        entries=entries,
        total=len(entries),
        query_time_ms=query_time_ms,
        mode=mode,
        query=query,
    )


# --- Search Result Caching (Improvement #5) ---

_search_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL: float = 300.0


def _cache_key(query: str, mode: str, **kwargs: Any) -> str:
    raw = f"{query}:{mode}:{json.dumps(kwargs, sort_keys=True, default=str)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _get_cached(key: str) -> Any | None:
    if key in _search_cache:
        ts, result = _search_cache[key]
        if time.monotonic() - ts < _CACHE_TTL:
            return result
        del _search_cache[key]
    return None


def _set_cached(key: str, result: Any) -> None:
    _search_cache[key] = (time.monotonic(), result)


def invalidate_cache() -> None:
    """Invalidate all cached search results."""
    _search_cache.clear()


# --- Watermark Tracking (Improvement #4) ---

_WATERMARK_SEVERITY = "__WATERMARK__"


def get_watermark(config: LongbowConfig | None = None) -> int | None:
    """Retrieve the last-ingested timestamp watermark (nanoseconds)."""
    if config is None:
        config = LongbowConfig()
    try:
        from gcloud_logs_anomaly_detection.longbow_client import get_client

        client = get_client(config)
        result = client.search(
            dataset=config.dataset,
            vector=[0.0] * config.dims,
            k=1,
            filters=[{"field": "severity", "op": "eq", "value": _WATERMARK_SEVERITY}],
        )
        if hasattr(result, "compute"):
            result = result.compute()
        if hasattr(result, "iloc") and len(result) > 0:
            return int(result.iloc[0].get("timestamp", 0))
    except Exception:
        logger.debug("No watermark found for dataset '%s'", config.dataset)
    return None


def set_watermark(timestamp_nanos: int, config: LongbowConfig | None = None) -> None:
    """Store the ingestion watermark timestamp."""
    if config is None:
        config = LongbowConfig()
    try:
        ensure_dataset(config)
        vector = [0.0] * config.dims
        metadata = [
            {
                "timestamp": timestamp_nanos,
                "severity": _WATERMARK_SEVERITY,
                "resource": "watermark",
                "message": "ingestion_watermark",
                "labels": "",
            }
        ]
        store_vectors(vector, metadata, config)
        logger.info("Updated watermark to %d ns", timestamp_nanos)
    except Exception as exc:
        logger.warning("Failed to set watermark: %s", exc)


# --- Async Batch Ingestion (Improvement #2) ---


def store_log_entries_async(
    entries: list[dict[str, Any]],
    config: LongbowConfig | None = None,
    max_workers: int = 4,
    batch_size: int = 500,
) -> int:
    """Embed and store log entries using concurrent batch processing.

    Splits entries into chunks, embeds them in parallel, then inserts
    completed batches as they finish.
    """
    if not entries:
        return 0
    if config is None:
        config = LongbowConfig()

    ensure_dataset(config)

    chunks = [entries[i : i + batch_size] for i in range(0, len(entries), batch_size)]
    total_stored = 0

    def _process_chunk(chunk: list[dict[str, Any]]) -> int:
        vectors = embed_log_entries(chunk, model_name=config.embedding_model)
        metadata = _build_metadata(chunk)
        return store_vectors(vectors, metadata, config)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_process_chunk, chunk): chunk for chunk in chunks}
        for future in as_completed(futures):
            try:
                count = future.result()
                total_stored += count
            except Exception as exc:
                logger.error("Batch ingest failed: %s", exc)

    logger.info("Async stored %d/%d entries in Longbow", total_stored, len(entries))
    return total_stored


def _build_metadata(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build metadata list from log entries."""
    metadata: list[dict[str, Any]] = []
    for entry in entries:
        ts = entry.get("timestamp")
        ts_nanos = 0
        if ts is not None:
            ts_nanos = (
                int(ts.timestamp() * 1000000000.0) if isinstance(ts, datetime) else int(ts)
            )
        metadata.append(
            {
                "timestamp": ts_nanos,
                "severity": str(entry.get("severity", "")),
                "resource": str(entry.get("resource", "")),
                "message": str(entry.get("message", "") or entry.get("payload", "")),
                "labels": str(entry.get("labels", "")),
            }
        )
    return metadata


# --- Core Store Operations ---


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
    invalidate_cache()
    vectors = embed_log_entries(entries, model_name=config.embedding_model)
    metadata = _build_metadata(entries)

    count = store_vectors(vectors, metadata, config)
    logger.info("Stored %d log entries in Longbow dataset '%s'", count, config.dataset)
    return count


def store_log_entries_incremental(
    entries: list[dict[str, Any]],
    config: LongbowConfig | None = None,
) -> int:
    """Store entries with watermark tracking to avoid duplicates.

    Only entries newer than the last watermark are stored.
    """
    if not entries:
        return 0
    if config is None:
        config = LongbowConfig()

    watermark = get_watermark(config)
    if watermark is not None:
        filtered = []
        for e in entries:
            ts = e.get("timestamp")
            ts_nanos = 0
            if ts is not None:
                ts_nanos = (
                    int(ts.timestamp() * 1000000000.0)
                    if isinstance(ts, datetime)
                    else int(ts)
                )
            if ts_nanos > watermark:
                filtered.append(e)
        logger.info(
            "Filtered %d -> %d entries (watermark: %d ns)",
            len(entries),
            len(filtered),
            watermark,
        )
        entries = filtered

    if not entries:
        logger.info("No new entries to ingest")
        return 0

    count = store_log_entries(entries, config)

    max_ts = 0
    for e in entries:
        ts = e.get("timestamp")
        if ts is not None:
            ts_nanos = (
                int(ts.timestamp() * 1000000000.0)
                if isinstance(ts, datetime)
                else int(ts)
            )
            max_ts = max(max_ts, ts_nanos)
    if max_ts > 0:
        set_watermark(max_ts, config)

    return count


# --- Search Operations ---


def search_similar_logs(
    query: str,
    k: int = 10,
    config: LongbowConfig | None = None,
    *,
    use_cache: bool = True,
) -> Any:
    """Semantic search: find logs similar to a text query.

    Returns SearchResult if structured=True, else DataFrame.
    """
    if config is None:
        config = LongbowConfig()

    key = _cache_key(query, "dense", k=k)
    if use_cache:
        cached = _get_cached(key)
        if cached is not None:
            return cached

    start = time.monotonic()
    vector = embed_text(query, model_name=config.embedding_model)
    result = search_vectors(vector, k=k, config=config)
    if hasattr(result, "compute"):
        result = result.compute()
    elapsed_ms = (time.monotonic() - start) * 1000

    search_result = _df_to_search_result(result, "dense", query, elapsed_ms)
    if use_cache:
        _set_cached(key, search_result)
    return search_result


def search_filtered_logs(
    query: str,
    filters: list[dict[str, Any]],
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Filtered search: combine semantic similarity with metadata filters.

    Filters example: [{"field": "severity", "op": "eq", "value": "ERROR"}]
    Supports: eq, neq, gt, gte, lt, lte, in, like
    """
    if config is None:
        config = LongbowConfig()

    start = time.monotonic()
    vector = embed_text(query, model_name=config.embedding_model)
    result = search_filtered(vector, filters=filters, k=k, config=config)
    if hasattr(result, "compute"):
        result = result.compute()
    elapsed_ms = (time.monotonic() - start) * 1000

    return _df_to_search_result(result, "filtered", query, elapsed_ms)


def search_hybrid_logs(
    query: str,
    text_query: str | None = None,
    alpha: float = 0.7,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Hybrid search: combine dense + sparse retrieval with RRF."""
    if config is None:
        config = LongbowConfig()

    start = time.monotonic()
    vector = embed_text(query, model_name=config.embedding_model)
    result = search_hybrid(
        vector, text_query=text_query, alpha=alpha, k=k, config=config
    )
    if hasattr(result, "compute"):
        result = result.compute()
    elapsed_ms = (time.monotonic() - start) * 1000

    return _df_to_search_result(result, "hybrid", query, elapsed_ms)


def search_temporal_logs(
    search_type: str = "sliding_window_time",
    duration: str = "1h",
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Temporal search: query logs within a time window."""
    if config is None:
        config = LongbowConfig()

    start = time.monotonic()
    result = search_temporal(
        search_type=search_type, duration=duration, k=k, config=config
    )
    if hasattr(result, "compute"):
        result = result.compute()
    elapsed_ms = (time.monotonic() - start) * 1000

    return _df_to_search_result(result, "temporal", "", elapsed_ms)


def search_logs_by_id(
    vector_id: int,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Find logs similar to a known log entry by its Longbow ID."""
    if config is None:
        config = LongbowConfig()

    start = time.monotonic()
    result = search_by_id(vector_id, k=k, config=config)
    if hasattr(result, "compute"):
        result = result.compute()
    elapsed_ms = (time.monotonic() - start) * 1000

    return _df_to_search_result(result, "by-id", str(vector_id), elapsed_ms)


def search_turboquant_logs(
    query: str,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Search compressed TurboQuant vectors."""
    if config is None:
        config = LongbowConfig()

    start = time.monotonic()
    vector = embed_text(query, model_name=config.embedding_model)
    result = search_turboquant(vector, k=k, config=config)
    if hasattr(result, "compute"):
        result = result.compute()
    elapsed_ms = (time.monotonic() - start) * 1000

    return _df_to_search_result(result, "turboquant", query, elapsed_ms)
