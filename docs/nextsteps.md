# Next Steps — Longbow & Longbow-Quarrel Integration

> Replaces previous improvement plan. Generated from analysis of
> [longbow](https://github.com/23skdu/longbow) (v0.1.9+) and
> [longbow-quarrel](https://github.com/23skdu/longbow-quarrel) (v0.2.0).

## Integration Overview

Add two major capabilities to gcloud_logs_anomaly_detection:

1. **Longbow** — Store log entries as vectors for high-performance similarity search, filtering, temporal queries, and knowledge graph traversal.
2. **Longbow-Quarrel** — Use as an alternative local inference backend (OpenAI-compatible API) instead of Ollama or Google Gemini.

---

## Step 1: Add Dependencies

**Files:** `requirements.txt`, `pyproject.toml`, `Dockerfile`

Add:
- `longbow` — Python SDK (`pip install longbow`)
- `openai` — Used by Quarrel's OpenAI-compatible endpoint

Update:
```
requirements.txt:
+ longbow>=0.1.9
+ openai>=1.0.0

pyproject.toml [project.dependencies]:
+ "longbow>=0.1.9",
+ "openai>=1.0.0",

Dockerfile: no change needed (installed via requirements.txt)
```

---

## Step 2: Add Longbow Configuration

**File:** `gcloud_logs_anomaly_detection/config.py`

Add new pydantic settings class:

```python
class LongbowConfig(BaseSettings):
    """Configuration for Longbow vector storage."""
    uri: str = Field(default="grpc://localhost:3000", description="Longbow data port URI")
    meta_uri: str = Field(default="grpc://localhost:3001", description="Longbow meta port URI")
    dataset: str = Field(default="gcloud_logs", description="Longbow dataset name")
    dims: int = Field(default=384, description="Embedding dimensions")
    data_type: str = Field(default="float32", description="Vector data type (float32|turboquant|int8)")
    turboquant_bits: int = Field(default=4, description="TurboQuant compression bits (2|4|8)")
    search_k: int = Field(default=10, description="Default k for search")
    search_alpha: float = Field(default=0.7, description="Alpha for hybrid search (1.0=dense, 0.0=sparse)")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", description="Sentence-transformers model for embeddings")

    model_config = SettingsConfigDict(env_prefix="LONGBOW_", extra="ignore")
```

Add env vars to `.env.example`:
```
# Longbow Vector Storage
LONGBOW_URI=grpc://localhost:3000
LONGBOW_META_URI=grpc://localhost:3001
LONGBOW_DATASET=gcloud_logs
LONGBOW_DIMS=384
LONGBOW_DATA_TYPE=float32
LONGBOW_SEARCH_K=10
```

---

## Step 3: Add Quarrel Configuration

**File:** `gcloud_logs_anomaly_detection/config.py`

```python
class QuarrelConfig(BaseSettings):
    """Configuration for Longbow-Quarrel inference."""
    base_url: str = Field(default="http://localhost:8080", description="Quarrel API base URL")
    api_key: str = Field(default="", description="Quarrel API key (env: QUARREL_API_KEY)")
    model: str = Field(default="default", description="Quarrel model name")
    temperature: float = Field(default=0.0, description="LLM temperature")
    max_tokens: int = Field(default=4096, description="Max tokens for generation")

    model_config = SettingsConfigDict(env_prefix="QUARREL_", extra="ignore")
```

Add env vars to `.env.example`:
```
# Longbow-Quarrel Inference
QUARREL_BASE_URL=http://localhost:8080
QUARREL_API_KEY=
QUARREL_MODEL=default
```

---

## Step 4: Create Embedding Utility

**New file:** `gcloud_logs_anomaly_detection/embeddings.py`

Responsibilities:
- Load a sentence-transformers model (default: `all-MiniLM-L6-v2`, 384 dims)
- Embed a single string or batch of strings
- Embed a log entry dict (combining timestamp, severity, message, resource into text)
- Provide a `embed_log_entries(entries: list[dict]) -> list[list[float]]` function

```python
from sentence_transformers import SentenceTransformer

_model = None

def get_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(model_name)
    return _model

def embed_text(text: str, model_name: str = "all-MiniLM-L6-v2") -> list[float]:
    model = get_model(model_name)
    return model.encode(text).tolist()

def embed_log_entry(entry: dict, model_name: str = "all-MiniLM-L6-v2") -> list[float]:
    text = f"{entry.get('severity', '')} {entry.get('message', '')} {entry.get('resource', '')}"
    return embed_text(text, model_name)

def embed_log_entries(entries: list[dict], model_name: str = "all-MiniLM-L6-v2") -> list[list[float]]:
    texts = [
        f"{e.get('severity', '')} {e.get('message', '')} {e.get('resource', '')}"
        for e in entries
    ]
    model = get_model(model_name)
    return model.encode(texts).tolist()
```

Add `sentence-transformers` to dependencies:
```
requirements.txt:
+ sentence-transformers>=3.0.0
```

---

## Step 5: Create Longbow Vector Storage Module

**New file:** `gcloud_logs_anomaly_detection/longbow_store.py`

This module provides the core integration with Longbow for storing and searching log vectors.

### Key Functions

```python
from longbow import LongbowClient
from gcloud_logs_anomaly_detection.config import LongbowConfig

def get_client(config: LongbowConfig | None = None) -> LongbowClient:
    """Create and return a connected Longbow client."""

def ensure_dataset(client: LongbowClient, config: LongbowConfig) -> None:
    """Create the dataset/namespace if it doesn't exist."""

def store_log_entries(
    entries: list[dict],
    config: LongbowConfig | None = None,
) -> int:
    """Embed and store log entries in Longbow. Returns count stored.
    
    Each entry is stored with metadata:
    - timestamp (int64, nanoseconds)
    - severity (string)
    - resource (string)
    - message (string)
    - labels (JSON string)
    """

def search_similar_logs(
    query: str,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> pd.DataFrame:
    """Semantic search: find logs similar to a text query.
    Uses Dense search via client.search().
    """

def search_filtered(
    query: str,
    filters: list[dict],
    k: int = 10,
    config: LongbowConfig | None = None,
) -> pd.DataFrame:
    """Filtered search: combine semantic similarity with metadata filters.
    Filters example: [{"field": "severity", "op": "eq", "value": "ERROR"}]
    Supports: eq, neq, gt, gte, lt, lte, in, like
    """

def search_hybrid(
    query: str,
    text_query: str | None = None,
    alpha: float = 0.7,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> pd.DataFrame:
    """Hybrid search: combine dense (vector) + sparse (BM25) retrieval.
    alpha=1.0 is pure dense, alpha=0.0 is pure sparse.
    """

def search_temporal(
    search_type: str = "sliding_window_time",
    duration: str = "1h",
    k: int = 10,
    config: LongbowConfig | None = None,
) -> pd.DataFrame:
    """Temporal search: query logs within a time window.
    search_type: "as_of" | "range" | "sliding_window" | "sliding_window_time"
    """

def search_by_id(
    vector_id: int,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> pd.DataFrame:
    """Find logs similar to a known log entry by its Longbow ID."""

def search_turboquant(
    query: str,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> pd.DataFrame:
    """Search compressed TurboQuant vectors (4-64x storage reduction)."""

def get_cluster_stats(config: LongbowConfig | None = None) -> dict:
    """Return dataset stats: vector count, node count, memory usage."""
```

---

## Step 6: Add Longbow-Search Subcommand

**File:** `gcloud_logs_anomaly_detection/cli.py`

Add a new `search` subcommand with multiple search modes:

```
gcloud-anomaly search "authentication failures" --mode dense --k 10
gcloud-anomaly search "errors" --mode filtered --filter severity=ERROR
gcloud-anomaly search "timeout" --mode hybrid --alpha 0.7
gcloud-anomaly search --mode temporal --duration 1h
gcloud-anomaly search --mode by-id --id 12345
gcloud-anomaly search "disk full" --mode turboquant
```

CLI options:
- `QUERY` (optional text query for dense/filtered/hybrid/turboquant)
- `--mode` : dense | sparse | filtered | hybrid | by-id | temporal | turboquant (default: dense)
- `--k` : number of results (default: 10)
- `--alpha` : hybrid blending weight (default: 0.7)
- `--filter` : KEY=OP:VALUE pairs (e.g., `severity=eq:ERROR`, `resource=like:compute`)
- `--duration` : time window for temporal (e.g., `1h`, `30m`, `1d`)
- `--dataset` : override dataset name

---

## Step 7: Add Quarrel as Inference Backend

**New file:** `gcloud_logs_anomaly_detection/quarrel_llm.py`

Create a LangChain-compatible LLM wrapper around Quarrel's OpenAI-compatible API:

```python
from langchain_core.language_models.llms import LLM
from openai import OpenAI

class QuarrelLLM(LLM):
    """LangChain LLM wrapper for Longbow-Quarrel OpenAI-compatible API."""
    
    base_url: str = "http://localhost:8080"
    api_key: str = ""
    model: str = "default"
    temperature: float = 0.0
    max_tokens: int = 4096

    def _call(self, prompt: str, stop: list[str] | None = None, **kwargs) -> str:
        client = OpenAI(base_url=self.base_url, api_key=self.api_key or "none")
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""

    @property
    def _llm_type(self) -> str:
        return "quarrel"
```

Add a factory function:
```python
def create_quarrel_llm(config: QuarrelConfig | None = None) -> QuarrelLLM:
    """Create a Quarrel LLM instance from config."""
```

---

## Step 8: Integrate Quarrel into LLM Summarization

**File:** `gcloud_logs_anomaly_detection/gcloud_logs_llmsummary.py`

Add a `--backend` option to select inference source:
- `gemini` (default) — Google Gemini via langchain-google-genai
- `quarrel` — Longbow-Quarrel local inference
- `ollama` — Ollama via langchain-ollama

Modify `create_llm()`:
```python
def create_llm(model_name: str, temperature: float = 0.0, backend: str = "gemini") -> Any:
    """Create LLM instance for the specified backend."""
    if backend == "quarrel":
        from gcloud_logs_anomaly_detection.quarrel_llm import create_quarrel_llm
        return create_quarrel_llm()
    elif backend == "ollama":
        from langchain_ollama import OllamaLLM
        return OllamaLLM(model=model_name)
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model_name, temperature=temperature)
```

Add CLI option:
```
gcloud-anomaly summarize --backend quarrel
gcloud-anomaly summarize --backend gemini
gcloud-anomaly summarize --backend ollama
```

---

## Step 9: Integrate Longbow into Anomaly Detection Pipeline

**File:** `gcloud_logs_detect.py`

After detecting anomalies, optionally store results in Longbow:

```python
def store_anomaly_results(
    df: pd.DataFrame,
    config: LongbowConfig | None = None,
) -> int:
    """Store detected anomalies in Longbow for future similarity search.
    
    Converts each row to a log entry dict with metadata:
    - timestamp, severity, message_length, anomaly (bool), score
    """
```

Add CLI flag:
```
gcloud-anomaly detect --store-vector   # Store results in Longbow
```

---

## Step 10: Create Vector Ingestion CLI Command

**File:** `gcloud_logs_anomaly_detection/cli.py`

New subcommand for batch ingestion from GCP into Longbow:

```
gcloud-anomaly ingest --log-name compute --hours-ago 24
gcloud-anomaly ingest --log-name audit --filter "severity >= ERROR" --hours-ago 72
```

Flow:
1. Fetch logs from GCP using `get_log_entries()` from `gcloud_logs_llmsummary.py`
2. Embed using `embed_log_entries()` from `embeddings.py`
3. Store in Longbow using `store_log_entries()` from `longbow_store.py`
4. Emit metrics: count stored, embedding time, storage time

---

## Step 11: Create Longbow Client Module

**New file:** `gcloud_logs_anomaly_detection/longbow_client.py`

Thin wrapper providing:
- Connection management (connect/disconnect/reconnect)
- Dataset creation with configurable schema
- Batch insert with automatic chunking (Longbow handles Dask natively)
- Search dispatch based on mode string
- Error handling and retry logic (circuit breaker: 10 failures, 30s cooldown)

---

## Step 12: Add Tests

**Files:** `tests/test_embeddings.py`, `tests/test_longbow_store.py`, `tests/test_quarrel_llm.py`

### test_embeddings.py
- Test `embed_text()` returns correct dimensions (384 for MiniLM)
- Test `embed_log_entry()` formats entry correctly
- Test `embed_log_entries()` handles empty list
- Mock `SentenceTransformer` for unit tests

### test_longbow_store.py
- Test `store_log_entries()` with mocked LongbowClient
- Test `search_similar_logs()` returns DataFrame
- Test `search_filtered()` builds correct filter expressions
- Test `search_hybrid()` passes alpha correctly
- Test `search_temporal()` handles all search_type variants
- Test `ensure_dataset()` creates namespace on first call
- Mock all Longbow SDK calls

### test_quarrel_llm.py
- Test `QuarrelLLM._call()` with mocked OpenAI client
- Test `create_quarrel_llm()` from config
- Test fallback behavior when Quarrel is unreachable
- Mock `openai.OpenAI` client

---

## Step 13: Update Docker & Compose

**File:** `Dockerfile`

Add `sentence-transformers` to pip install (already in requirements.txt).

**New file:** `docker-compose.longbow.yml`

```yaml
services:
  longbow:
    image: ghcr.io/23skdu/longbow:latest
    ports:
      - "3000:3000"
      - "3001:3001"
      - "9090:9090"
    environment:
      - LONGBOW_MAX_MEMORY=2GB

  quarrel:
    image: ghcr.io/23skdu/longbow-quarrel:latest
    ports:
      - "8080:8080"
    environment:
      - QUARREL_API_KEY=${QUARREL_API_KEY}
    volumes:
      - ~/.cache/llmfit/models:/root/.cache/llmfit/models

  anomaly-detection:
    build: .
    depends_on:
      - longbow
      - quarrel
    environment:
      - LONGBOW_URI=grpc://longbow:3000
      - LONGBOW_META_URI=grpc://longbow:3001
      - QUARREL_BASE_URL=http://quarrel:8080
      - GCP_PROJECT=${GCP_PROJECT}
    volumes:
      - ~/.config/gcloud:/home/appuser/.config/gcloud
```

---

## Step 14: Update Environment Configuration

**File:** `.env.example`

Add:
```
# Longbow Vector Storage
LONGBOW_URI=grpc://localhost:3000
LONGBOW_META_URI=grpc://localhost:3001
LONGBOW_DATASET=gcloud_logs
LONGBOW_DIMS=384
LONGBOW_DATA_TYPE=float32
LONGBOW_SEARCH_K=10
LONGBOW_SEARCH_ALPHA=0.7
LONGBOW_EMBEDDING_MODEL=all-MiniLM-L6-v2

# Longbow-Quarrel Inference
QUARREL_BASE_URL=http://localhost:8080
QUARREL_API_KEY=
QUARREL_MODEL=default
QUARREL_TEMPERATURE=0.0
QUARREL_MAX_TOKENS=4096
```

---

## Step 15: Update Documentation

**Files to update:**
- `README.md` — Add Longbow/Quarrel sections, architecture diagram
- `docs/nextsteps.md` — Mark completed, add new items
- New: `docs/longbow.md` — Full Longbow integration guide
- New: `docs/quarrel.md` — Quarrel inference guide

---

## Execution Order

| Phase | Steps | Dependencies |
|-------|-------|-------------|
| 1. Foundation | 1, 2, 3, 4 | None |
| 2. Core | 5, 7, 11 | Phase 1 |
| 3. CLI | 6, 8, 9, 10 | Phase 2 |
| 4. Testing | 12 | Phase 3 |
| 5. Deploy | 13, 14, 15 | Phase 4 |

---

## Search Modes Supported via Longbow

| Mode | CLI Flag | Description | Use Case |
|------|----------|-------------|----------|
| Dense | `--mode dense` | HNSW vector similarity | "Find logs like this one" |
| Sparse | `--mode sparse` | BM25 keyword matching | Exact keyword search |
| Filtered | `--mode filtered` | Metadata predicate filtering | "ERROR logs in compute zone" |
| Hybrid | `--mode hybrid` | RRF-fused dense + sparse | Best of both worlds |
| ByID | `--mode by-id` | O(1) specific vector lookup | "Find neighbors of log #12345" |
| Temporal | `--mode temporal` | Time-window queries | "Last hour of errors" |
| TurboQuant | `--mode turboquant` | Compressed vector search | Low-storage archival search |

---

## API Surface Summary

### Longbow Python SDK (`pip install longbow`)
- `LongbowClient(uri, meta_uri)` — connection
- `client.insert(dataset, ddf)` — batch ingest via Dask
- `client.search(dataset, vector, k, alpha, filters, ...)` — multi-mode search
- `client.search_by_id(dataset, id, k)` — by-ID lookup
- `client.temporal_search(dataset, search_type, ...)` — time-travel queries
- `client.geo_search(dataset, center, radius_km, ...)` — geo-spatial
- `client.recommend(dataset, seed_ids, ...)` — GraphRAG
- `client.create_namespace(name, dims, data_type, ...)` — dataset creation

### Longbow-Quarrel OpenAI-Compatible API
- `POST /v1/chat/completions` — chat completions (OpenAI format)
- `POST /v1/completions` — legacy completions
- `POST /generate` — simple generation
- `POST /stream` — SSE streaming
- `GET /models` — list models
- `POST /hotswap` — hot-swap model
- `GET /health` — health check
