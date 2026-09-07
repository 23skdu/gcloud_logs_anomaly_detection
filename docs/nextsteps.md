# Next Steps — Improvement Plan

> Generated from deep code analysis of gcloud-logs-anomaly-detection.
> All Longbow/Quarrel integration steps (1-15) are **fully implemented**.
> See `docs/longbow.md` and `docs/quarrel.md` for integration guides.

## Completed Integration Summary

The following integration work is complete and verified:

- **Dependencies**: `longbow`, `openai`, `sentence-transformers` in requirements.txt/pyproject.toml
- **Config**: `LongbowConfig` and `QuarrelConfig` pydantic settings classes
- **Embeddings**: `embeddings.py` with `embed_text()`, `embed_log_entry()`, `embed_log_entries()`
- **Vector Storage**: `longbow_store.py` with all search modes (dense, sparse, filtered, hybrid, by-id, temporal, turboquant)
- **Longbow Client**: `longbow_client.py` with connection management, dataset creation, batch insert
- **Quarrel LLM**: `quarrel_llm.py` with LangChain-compatible `QuarrelLLM` wrapper
- **CLI**: `search` (7 modes), `ingest`, `--backend` (gemini/quarrel/ollama), `--store-vector` commands
- **Docker**: `Dockerfile` + `docker-compose.longbow.yml` with healthchecks
- **Tests**: `test_embeddings.py`, `test_longbow_store.py`, `test_quarrel_llm.py`
- **Docs**: `docs/longbow.md`, `docs/quarrel.md`, updated `README.md`

---

## 10-Part Improvement Plan

### 1. Circuit Breaker for Longbow Client

**File:** `gcloud_logs_anomaly_detection/longbow_client.py`

Add a circuit breaker pattern to prevent cascade failures when Longbow is unreachable.

**Spec:**
- Track consecutive failures per operation (connect, insert, search)
- After 10 consecutive failures, open circuit for 30 seconds
- During open circuit, raise `LongbowCircuitOpen` immediately
- After cooldown, allow one probe request; close on success
- Emit `log_metric("circuit_breaker_open", ...)` on state change

```python
class CircuitBreaker:
    failure_threshold: int = 10
    cooldown_seconds: float = 30.0
    state: Literal["closed", "open", "half_open"]
```

**Priority:** High — prevents cascading timeouts in production

---

### 2. Async Batch Ingestion

**Files:** `gcloud_logs_anomaly_detection/longbow_store.py`, `cli.py`

Add async/concurrent ingestion for large log volumes (100k+ entries).

**Spec:**
- Add `store_log_entries_async(entries, config, max_workers=4)` using `concurrent.futures.ThreadPoolExecutor`
- Chunk entries into batches of 500 (Longbow's optimal batch size)
- Embed batches concurrently via `SentenceTransformer.encode(batch)` with thread pool
- Insert completed chunks as they finish (pipeline embed → insert)
- Add `--workers` option to `gcloud-anomaly ingest`
- Emit metrics: `ingest_batch_size`, `ingest_duration`, `ingest_throughput`

**Priority:** High — current single-threaded path blocks on large volumes

---

### 3. Health Check CLI Command

**File:** `gcloud_logs_anomaly_detection/cli.py`

Add `gcloud-anomaly health` to verify all service connectivity.

**Spec:**
- `gcloud-anomaly health` — checks all configured backends
- `gcloud-anomaly health --longbow` — tests Longbow gRPC connection + dataset exists
- `gcloud-anomaly health --quarrel` — tests Quarrel HTTP `/health` endpoint
- `gcloud-anomaly health --gemini` — validates GCP credentials + model access
- Return exit code 0 if all healthy, 1 if any failed
- Output: JSON status per service with latency measurements

**Priority:** Medium — essential for Docker Compose / K8s readiness probes

---

### 4. Incremental Ingestion with Watermark Tracking

**File:** `gcloud_logs_anomaly_detection/longbow_store.py`

Track last-ingested timestamp to avoid re-ingesting duplicate log entries.

**Spec:**
- Store watermark (last ingested timestamp) as metadata in Longbow dataset
- On `ingest`, query watermark first, only fetch logs newer than watermark
- Add `--since` flag to override watermark (force full re-ingest)
- Add `--reset-watermark` flag to clear stored watermark
- Store watermark as special vector with `metadata.type = "watermark"`
- Log: `Ingesting from {watermark} to {now} ({count} new entries)`

**Priority:** High — prevents duplicate storage and reduces GCP API costs

---

### 5. Search Result Caching

**File:** `gcloud_logs_anomaly_detection/longbow_store.py`

Cache frequent search results to reduce embedding compute and Longbow queries.

**Spec:**
- Add `@lru_cache`-based caching for `embed_text()` (same query → same vector)
- Add optional Redis-backed cache for search results (key: `sha256(query + params)`)
- Cache TTL: configurable via `LONGBOW_CACHE_TTL` env var (default: 300s)
- Cache invalidation on `store_log_entries()` call
- Add `--no-cache` flag to search commands
- Emit metric: `search_cache_hit` / `search_cache_miss`

**Priority:** Medium — reduces latency for repeated queries in dashboards

---

### 6. Structured Search Response Format

**Files:** `gcloud_logs_anomaly_detection/longbow_store.py`, `cli.py`

Return structured search results instead of raw DataFrame strings.

**Spec:**
- Add `SearchResult` dataclass: `entries: list[LogEntry], total: int, query_time_ms: float, mode: str`
- Add `LogEntry` dataclass: `id: int, score: float, timestamp: str, severity: str, message: str, resource: str, labels: dict`
- Add `--format` flag: `table` (default, current), `json`, `csv`
- `--format json` outputs `SearchResult` as JSON for programmatic consumption
- `--format csv` outputs CSV for piping to other tools
- Keep backward-compatible default (table format)

**Priority:** Medium — enables integration with external tools and scripts

---

### 7. Log Entry Schema Normalization

**File:** `gcloud_logs_anomaly_detection/embeddings.py`

Standardize log entry schema across different GCP log types (audit, VPC Flow, App Engine, etc.).

**Spec:**
- Define `LogEntrySchema` TypedDict with normalized fields: `timestamp`, `severity`, `message`, `resource`, `labels`, `log_name`, `insert_id`
- Add `normalize_entry(raw_entry, log_type)` function that maps GCP-specific fields to schema
- Support log types: `audit`, `vpc_flow`, `app_engine`, `cloud_run`, `generic`
- `_entry_to_text()` uses normalized schema for consistent embedding
- Add `normalize_entries(entries, log_type="generic")` batch function
- Unit tests for each log type normalization

**Priority:** Medium — ensures consistent embedding quality across log sources

---

### 8. Metrics Export to Prometheus/OpenTelemetry

**File:** `gcloud_logs_anomaly_detection/observability.py`

Export structured metrics for monitoring dashboards.

**Spec:**
- Add optional `prometheus_client` integration (lazy import)
- Export metrics: `anomaly_detection_total`, `log_entries_processed_total`, `search_queries_total`, `ingest_vectors_total`, `llm_summarization_duration_seconds`
- Add `--metrics-port` flag (default: 9090) to expose `/metrics` endpoint
- Add `METRICS_ENABLED` env var to toggle
- Keep existing `log_metric()` as fallback when prometheus unavailable
- Add Grafana dashboard JSON template in `docs/grafana/`

**Priority:** Low — useful for production monitoring but not blocking

---

### 9. Plugin Architecture for LLM Backends

**Files:** `gcloud_logs_anomaly_detection/config.py`, `gcloud_logs_llmsummary.py`

Make LLM backends pluggable via Python entry points.

**Spec:**
- Define `LLMBackend` protocol: `def create(model_name, temperature, **kwargs) -> Any`
- Register backends via `pyproject.toml` entry points: `[project.entry-points."gcloud_anomaly.llm"]`
- Built-in backends: `gemini`, `quarrel`, `ollama`
- Discover backends at runtime via `importlib.metadata.entry_points()`
- `--backend` accepts any registered backend name
- Custom backends: drop a package with entry point, no code changes needed
- Add `gcloud-anomaly backends` command to list available backends

**Priority:** Low — extensibility feature for community contributions

---

### 10. Integration Test Suite

**Files:** `tests/test_integration.py`, `tests/conftest.py`

Add integration tests that verify end-to-end workflows with mocked external services.

**Spec:**
- `conftest.py`: Fixtures for mocked Longbow client, Quarrel server, GCP Logging
- `test_integration_detect_store_search`: detect → store → search flow
- `test_integration_ingest_search`: ingest → search flow
- `test_integration_summarize_quarrel`: summarize with quarrel backend
- `test_integration_health_check`: health command returns expected format
- `test_integration_circuit_breaker`: circuit opens after failures, recovers after cooldown
- `test_integration_incremental_ingest`: watermark tracking prevents duplicates
- Use `pytest-httpserver` for Quarrel mock, `pytest-mock` for Longbow/GCP
- Target: 90%+ coverage on integration paths

**Priority:** High — prevents regressions in critical workflows

---

## Execution Order

| Phase | Improvements | Dependencies |
|-------|-------------|-------------|
| 1. Reliability | 1, 3 | None |
| 2. Performance | 2, 5 | None |
| 3. Data Integrity | 4, 7 | Phase 2 |
| 4. Observability | 6, 8 | Phase 1 |
| 5. Extensibility | 9 | Phase 4 |
| 6. Validation | 10 | All phases |

---

## Reference: API Surface (Implemented)

### Longbow Python SDK
- `LongbowClient(uri, meta_uri)` — connection
- `client.insert(dataset, ddf)` — batch ingest via Dask
- `client.search(dataset, vector, k, alpha, filters, ...)` — multi-mode search
- `client.search_by_id(dataset, id, k)` — by-ID lookup
- `client.temporal_search(dataset, search_type, ...)` — time-travel queries
- `client.create_namespace(name, dims, data_type, ...)` — dataset creation

### Longbow-Quarrel OpenAI-Compatible API
- `POST /v1/chat/completions` — chat completions
- `POST /v1/completions` — legacy completions
- `POST /generate` — simple generation
- `POST /stream` — SSE streaming
- `GET /models` — list models
- `GET /health` — health check

### Search Modes

| Mode | CLI Flag | Description | Use Case |
|------|----------|-------------|----------|
| Dense | `--mode dense` | HNSW vector similarity | "Find logs like this one" |
| Sparse | `--mode sparse` | BM25 keyword matching | Exact keyword search |
| Filtered | `--mode filtered` | Metadata predicate filtering | "ERROR logs in compute zone" |
| Hybrid | `--mode hybrid` | RRF-fused dense + sparse | Best of both worlds |
| ByID | `--mode by-id` | O(1) specific vector lookup | "Find neighbors of log #12345" |
| Temporal | `--mode temporal` | Time-window queries | "Last hour of errors" |
| TurboQuant | `--mode turboquant` | Compressed vector search | Low-storage archival search |
