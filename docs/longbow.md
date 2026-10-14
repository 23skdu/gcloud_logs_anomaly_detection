# Longbow Integration Guide

This document describes how to use [Longbow](https://github.com/23skdu/longbow) vector storage with gcloud-logs-anomaly-detection.

## Overview

Longbow provides high-performance vector storage for log entries, enabling:

- **Semantic search** across your log history
- **Filtered search** with metadata predicates
- **Hybrid search** combining vector similarity with keyword matching
- **Temporal search** for time-window queries
- **Compressed storage** via TurboQuant (4-64x reduction)
- **Circuit breaker** protection against cascading failures
- **Incremental ingestion** with watermark tracking to avoid duplicates

## Setup

### Prerequisites

1. A running Longbow instance (see [Longbow docs](https://github.com/23skdu/longbow))
2. Python dependencies: `pip install longbow sentence-transformers`

### Quick Start with Docker Compose

```bash
docker compose -f docker-compose.longbow.yml up longbow
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LONGBOW_URI` | Longbow data port URI | `grpc://localhost:3000` |
| `LONGBOW_META_URI` | Longbow meta port URI | `grpc://localhost:3001` |
| `LONGBOW_DATASET` | Dataset name | `gcloud_logs` |
| `LONGBOW_DIMS` | Embedding dimensions | `384` |
| `LONGBOW_DATA_TYPE` | Vector type (`float32`/`turboquant`/`int8`) | `float32` |
| `LONGBOW_SEARCH_K` | Default search results | `10` |
| `LONGBOW_SEARCH_ALPHA` | Hybrid blending (1.0=dense, 0.0=sparse) | `0.7` |
| `LONGBOW_EMBEDDING_MODEL` | Sentence-transformers model | `all-MiniLM-L6-v2` |

## CLI Commands

### Ingest Logs into Longbow

```bash
# Standard ingestion
gcloud-anomaly ingest --log-name compute --hours-ago 24
gcloud-anomaly ingest --filter "severity >= ERROR" --hours-ago 72

# Incremental (skips already-ingested entries via watermark)
gcloud-anomaly ingest --incremental --hours-ago 24

# Async batch ingestion (parallel embedding + insert)
gcloud-anomaly ingest --async --workers 8 --hours-ago 168
```

### Search Logs

```bash
# Dense (semantic similarity)
gcloud-anomaly search "authentication failures"

# Filtered
gcloud-anomaly search "errors" --mode filtered --filter severity=eq:ERROR

# Hybrid (dense + sparse)
gcloud-anomaly search "timeout" --mode hybrid --alpha 0.7

# Temporal
gcloud-anomaly search --mode temporal --duration 1h

# By ID
gcloud-anomaly search --mode by-id --id 12345

# TurboQuant (compressed)
gcloud-anomaly search "disk full" --mode turboquant

# Output formats
gcloud-anomaly search "errors" --format json
gcloud-anomaly search "errors" --format csv
gcloud-anomaly search "errors" --format table  # default

# Bypass cache
gcloud-anomaly search "errors" --no-cache
```

### Detect Anomalies and Store

```bash
gcloud-anomaly detect --store-vector
```

### Health Check

```bash
# Check all services
gcloud-anomaly health

# Check specific services
gcloud-anomaly health --longbow
gcloud-anomaly health --quarrel
gcloud-anomaly health --gemini
```

## Search Modes

| Mode | CLI Flag | Description | Use Case |
|------|----------|-------------|----------|
| `dense` | `--mode dense` | HNSW vector similarity | "Find logs like this one" |
| `sparse` | `--mode sparse` | BM25 keyword matching | Exact keyword search |
| `filtered` | `--mode filtered` | Metadata predicate filtering | "ERROR logs in compute zone" |
| `hybrid` | `--mode hybrid` | RRF-fused dense + sparse | Best of both worlds |
| `by-id` | `--mode by-id` | O(1) specific vector lookup | "Find neighbors of log #12345" |
| `temporal` | `--mode temporal` | Time-window queries | "Last hour of errors" |
| `turboquant` | `--mode turboquant` | Compressed vector search | Low-storage archival search |

## Circuit Breaker

The Longbow client includes a circuit breaker to prevent cascade failures:

- **Threshold**: Opens after 10 consecutive failures
- **Cooldown**: 30 seconds before allowing a probe request
- **Half-open**: One probe request allowed; closes on success, reopens on failure
- **Metrics**: `circuit_breaker_open` and `circuit_breaker_closed` emitted via `log_metric()`

## Watermark Tracking

Incremental ingestion tracks the last-ingested timestamp to avoid duplicates:

```python
from gcloud_logs_anomaly_detection.longbow_store import (
    get_watermark,
    set_watermark,
    store_log_entries_incremental,
)

# Automatic: queries watermark, filters old entries, updates watermark
count = store_log_entries_incremental(entries)

# Manual watermark management
wm = get_watermark()  # Returns nanoseconds or None
set_watermark(1704067200000000000)  # Set to specific timestamp
```

## Search Result Caching

Search results are cached (TTL: 300s) to reduce embedding compute:

```python
from gcloud_logs_anomaly_detection.longbow_store import (
    search_similar_logs,
    invalidate_cache,
)

# Cached by default
result = search_similar_logs("error logs")

# Bypass cache
result = search_similar_logs("error logs", use_cache=False)

# Invalidate all cached results
invalidate_cache()
```

## Structured Search Results

Search returns `SearchResult` dataclass with `LogEntry` items:

```python
from gcloud_logs_anomaly_detection.longbow_store import search_similar_logs

result = search_similar_logs("error logs")
print(f"Found {result.total} results in {result.query_time_ms:.1f}ms")
print(f"Mode: {result.mode}")

for entry in result.entries:
    print(f"  [{entry.id}] score={entry.score:.4f} {entry.severity}: {entry.message}")

# Export formats
print(result.to_json())  # JSON string
print(result.to_csv())   # CSV string
```

## Python API

```python
from gcloud_logs_anomaly_detection.longbow_store import (
    store_log_entries,
    store_log_entries_async,
    store_log_entries_incremental,
    search_similar_logs,
    search_filtered_logs,
    search_hybrid_logs,
    search_temporal_logs,
    search_logs_by_id,
    search_turboquant_logs,
)

# Store logs (synchronous)
store_log_entries(log_entries)

# Store logs (async batch)
store_log_entries_async(log_entries, max_workers=4, batch_size=500)

# Store logs (incremental, with watermark)
store_log_entries_incremental(log_entries)

# Search
results = search_similar_logs("error in database", k=10)

# Filtered search
results = search_filtered_logs(
    "timeout",
    filters=[{"field": "severity", "op": "eq", "value": "ERROR"}],
)
```

## Client Module

Low-level Longbow SDK wrapper (`longbow_client.py`):

```python
from gcloud_logs_anomaly_detection.longbow_client import (
    get_client,
    disconnect,
    ensure_dataset,
    store_vectors,
    search_vectors,
    get_cluster_stats,
)

# Connection management
client = get_client()  # Creates/caches connection
disconnect()           # Clears cached client

# Dataset management
ensure_dataset()       # Creates namespace if needed

# Statistics
stats = get_cluster_stats()
```
