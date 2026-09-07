"""Observability utilities: timing decorator and structured logging."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("gcloud_anomaly")


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for the application."""
    fmt = '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'
    logging.basicConfig(level=level, format=fmt, force=True)


def timeit(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that logs execution time of a function."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info("Function '%s' completed in %.4fs", func.__name__, elapsed)
        return result

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def log_metric(name: str, value: Any) -> None:
    """Emit a structured metric log entry."""
    logger.info("metric=%s value=%s", name, value)
