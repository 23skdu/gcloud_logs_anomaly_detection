"""Longbow client wrapper for connection management and operations."""

from __future__ import annotations

import logging
from typing import Any

from gcloud_logs_anomaly_detection.config import LongbowConfig
from gcloud_logs_anomaly_detection.observability import log_metric, timeit

logger = logging.getLogger("gcloud_anomaly.longbow")

_client: Any = None


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
    logger.info("Connected to Longbow at %s", config.uri)
    return _client


def disconnect() -> None:
    """Disconnect the Longbow client."""
    global _client
    _client = None


@timeit
def ensure_dataset(config: LongbowConfig | None = None) -> None:
    """Create the dataset/namespace if it doesn't exist."""
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    try:
        client.create_namespace(
            name=config.dataset,
            dims=config.dims,
            data_type=config.data_type,
        )
        log_metric("dataset_created", config.dataset)
    except Exception:
        logger.debug("Dataset '%s' may already exist", config.dataset)


@timeit
def store_vectors(
    vectors: list[list[float]],
    metadata: list[dict[str, Any]],
    config: LongbowConfig | None = None,
) -> int:
    """Store vectors with metadata in Longbow. Returns count stored."""
    import pandas as pd

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
    log_metric("vectors_stored", count)
    return count


@timeit
def search_vectors(
    vector: list[float],
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Dense vector similarity search."""
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    return client.search(dataset=config.dataset, vector=vector, k=k)


@timeit
def search_filtered(
    vector: list[float],
    filters: list[dict[str, Any]],
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Filtered search with metadata predicates."""
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    return client.search(dataset=config.dataset, vector=vector, filters=filters, k=k)


@timeit
def search_hybrid(
    vector: list[float],
    text_query: str | None = None,
    alpha: float = 0.7,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Hybrid dense + sparse search with RRF fusion."""
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    kwargs: dict[str, Any] = {"dataset": config.dataset, "vector": vector, "k": k}
    if text_query is not None:
        kwargs["text_query"] = text_query
    kwargs["alpha"] = alpha
    return client.search(**kwargs)


@timeit
def search_temporal(
    search_type: str = "sliding_window_time",
    duration: str = "1h",
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Temporal time-window search."""
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    return client.temporal_search(
        dataset=config.dataset,
        search_type=search_type,
        duration=duration,
        k=k,
    )


@timeit
def search_by_id(
    vector_id: int,
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Find neighbors of a known vector by ID."""
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    return client.search_by_id(dataset=config.dataset, id=vector_id, k=k)


@timeit
def search_turboquant(
    vector: list[float],
    k: int = 10,
    config: LongbowConfig | None = None,
) -> Any:
    """Search compressed TurboQuant vectors."""
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    return client.search(
        dataset=config.dataset, vector=vector, k=k, vector_type="turboquant"
    )


def get_cluster_stats(config: LongbowConfig | None = None) -> dict[str, Any]:
    """Return dataset stats."""
    if config is None:
        config = LongbowConfig()
    client = get_client(config)
    try:
        info = client.get_flight_info(config.dataset)
        return {"dataset": config.dataset, "info": info}
    except Exception as exc:
        return {"dataset": config.dataset, "error": str(exc)}
