"""Longbow client wrapper for connection management and operations."""

from __future__ import annotations

import logging
import time
from typing import Any

from gcloud_logs_anomaly_detection.config import LongbowConfig
from gcloud_logs_anomaly_detection.observability import log_metric, timeit

logger = logging.getLogger("gcloud_anomaly.longbow")

_client: Any = None


class CircuitBreaker:
    """Circuit breaker pattern to prevent cascade failures.

    States:
        closed   - Normal operation, requests pass through
        open     - Failures exceeded threshold, requests blocked
        half_open - Cooldown expired, allowing one probe request
    """

    def __init__(
        self,
        failure_threshold: int = 10,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._failure_count = 0
        self._state: str = "closed"
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> str:
        if self._state == "open" and time.monotonic() - self._last_failure_time >= self.cooldown_seconds:
            self._state = "half_open"
        return self._state

    def record_success(self) -> None:
        if self._state == "half_open":
            logger.info("Circuit breaker: probe succeeded, closing circuit")
            log_metric("circuit_breaker_closed", 1)
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.warning(
                "Circuit breaker: opened after %d consecutive failures",
                self._failure_count,
            )
            log_metric("circuit_breaker_open", self._failure_count)

    def allow_request(self) -> bool:
        state = self.state
        if state == "closed":
            return True
        if state == "half_open":
            logger.info("Circuit breaker: allowing probe request")
            return True
        return False


class LongbowCircuitOpenError(Exception):
    """Raised when the Longbow circuit breaker is open."""


_circuit = CircuitBreaker()


def get_client(config: LongbowConfig | None = None) -> Any:
    """Create and return a connected Longbow client."""
    global _client
    if _client is not None:
        return _client
    if config is None:
        config = LongbowConfig()
    try:
        from longbowclientsdk import LongbowClient
    except ImportError:
        try:
            from longbow.vector import LongbowClient
        except ImportError:
            raise ImportError(
                "Longbow vector SDK is required. Install from: "
                "pip install git+https://github.com/23skdu/longbow.git#subdirectory=longbowclientsdk"
            ) from None

    _client = LongbowClient(uri=config.uri, meta_uri=config.meta_uri)
    _circuit.record_success()
    logger.info("Connected to Longbow at %s", config.uri)
    return _client


def disconnect() -> None:
    """Disconnect the Longbow client."""
    global _client
    _client = None


def _check_circuit() -> None:
    """Raise if circuit breaker is open."""
    if not _circuit.allow_request():
        raise LongbowCircuitOpenError(
            f"Circuit breaker open: {_circuit._failure_count} consecutive failures. "
            f"Retry in {_circuit.cooldown_seconds}s."
        )


def _record_operation(success: bool) -> None:
    """Record operation result with circuit breaker."""
    if success:
        _circuit.record_success()
    else:
        _circuit.record_failure()


@timeit
def ensure_dataset(config: LongbowConfig | None = None) -> None:
    """Create the dataset/namespace if it doesn't exist."""
    _check_circuit()
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    try:
        client.create_namespace(
            name=config.dataset,
            dims=config.dims,
            data_type=config.data_type,
        )
        _record_operation(True)
        log_metric("dataset_created", config.dataset)
    except Exception:
        _record_operation(False)
        logger.debug("Dataset '%s' may already exist", config.dataset)


@timeit
def store_vectors(
    vectors: list[list[float]],
    metadata: list[dict[str, Any]],
    config: LongbowConfig | None = None,
) -> int:
    """Store vectors with metadata in Longbow. Returns count stored."""
    import pandas as pd

    _check_circuit()
    if config is None:
        config = LongbowConfig()
    client = get_client(config)

    df = pd.DataFrame(
        {
            "id": range(len(vectors)),
            "vector": vectors,
            **{k: [m.get(k) for m in metadata] for k in metadata[0]},
        }
    )

    import dask.dataframe as dd

    ddf = dd.from_pandas(df, npartitions=max(1, len(vectors) // 500))
    client.insert(config.dataset, ddf)
    count = len(vectors)
    _record_operation(True)
    log_metric("vectors_stored", count)
    return count


@timeit
def search_vectors(
    vector: list[float],
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Dense vector similarity search."""
    _check_circuit()
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    result = client.search(dataset=config.dataset, vector=vector, k=k)
    _record_operation(True)
    return result


@timeit
def search_filtered(
    vector: list[float],
    filters: list[dict[str, Any]],
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Filtered search with metadata predicates."""
    _check_circuit()
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    result = client.search(dataset=config.dataset, vector=vector, filters=filters, k=k)
    _record_operation(True)
    return result


@timeit
def search_hybrid(
    vector: list[float],
    text_query: str | None = None,
    alpha: float = 0.7,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Hybrid dense + sparse search with RRF fusion."""
    _check_circuit()
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    kwargs: dict[str, Any] = {"dataset": config.dataset, "vector": vector, "k": k}
    if text_query is not None:
        kwargs["text_query"] = text_query
    kwargs["alpha"] = alpha
    result = client.search(**kwargs)
    _record_operation(True)
    return result


@timeit
def search_temporal(
    search_type: str = "sliding_window_time",
    duration: str = "1h",
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Temporal time-window search."""
    _check_circuit()
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    result = client.temporal_search(
        dataset=config.dataset,
        search_type=search_type,
        duration=duration,
        k=k,
    )
    _record_operation(True)
    return result


@timeit
def search_by_id(
    vector_id: int,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Find neighbors of a known vector by ID."""
    _check_circuit()
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    result = client.search_by_id(dataset=config.dataset, id=vector_id, k=k)
    _record_operation(True)
    return result


@timeit
def search_turboquant(
    vector: list[float],
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Search compressed TurboQuant vectors."""
    _check_circuit()
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    result = client.search(
        dataset=config.dataset, vector=vector, k=k, vector_type="turboquant"
    )
    _record_operation(True)
    return result


def get_cluster_stats(config: LongbowConfig | None = None) -> dict[str, Any]:
    """Return dataset stats."""
    _check_circuit()
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    try:
        info = client.get_flight_info(config.dataset)
        _record_operation(True)
        return {"dataset": config.dataset, "info": info}
    except Exception as exc:
        _record_operation(False)
        return {"dataset": config.dataset, "error": str(exc)}
