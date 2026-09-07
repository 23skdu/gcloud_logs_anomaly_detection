# Longbow Integration Guide

This document describes how to use [Longbow](https://github.com/23skdu/longbow) vector storage with gcloud-logs-anomaly-detection.

## Overview

Longbow provides high-performance vector storage for log entries, enabling:
- **Semantic search** across your log history
- **Filtered search** with metadata predicates
- **Hybrid search** combining vector similarity with keyword matching
- **Temporal search** for time-window queries
- **Compressed storage** via TurboQuant (4-64x reduction)

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
gcloud-anomaly ingest --log-name compute --hours-ago 24
gcloud-anomaly ingest --filter "severity >= ERROR" --hours-ago 72
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
```

### Detect Anomalies and Store

```bash
gcloud-anomaly detect --store-vector
```

## Search Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `dense` | HNSW vector similarity | "Find logs like this one" |
| `sparse` | BM25 keyword matching | Exact keyword search |
| `filtered` | Metadata predicate filtering | "ERROR logs in compute zone" |
| `hybrid` | RRF-fused dense + sparse | Best of both worlds |
| `by-id` | O(1) specific vector lookup | "Find neighbors of log #12345" |
| `temporal` | Time-window queries | "Last hour of errors" |
| `turboquant` | Compressed vector search | Low-storage archival search |

## Python API

```python
from gcloud_logs_anomaly_detection.longbow_store import (
    store_log_entries,
    search_similar_logs,
    search_filtered_logs,
    search_hybrid_logs,
    search_temporal_logs,
)

# Store logs
store_log_entries(log_entries)

# Search
results = search_similar_logs("error in database", k=10)

# Filtered search
results = search_filtered_logs(
    "timeout",
    filters=[{"field": "severity", "op": "eq", "value": "ERROR"}],
)
```
