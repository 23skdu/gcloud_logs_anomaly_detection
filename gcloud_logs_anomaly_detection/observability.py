"""Observability utilities: timing decorator, structured logging, metrics export."""

from __future__ import annotations

import contextlib
import logging
import os
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
    _prometheus_export(name, value)


# --- Prometheus Metrics Export (Improvement #8) ---

_metrics_enabled: bool = os.environ.get("METRICS_ENABLED", "").lower() in ("1", "true", "yes")
_metrics: dict[str, float] = {}


def _prometheus_export(name: str, value: Any) -> None:
    """Export metric to Prometheus if enabled."""
    if not _metrics_enabled:
        return
    with contextlib.suppress(ValueError, TypeError):
        _metrics[name] = float(value)


def get_metrics() -> dict[str, float]:
    """Return all collected metrics."""
    return dict(_metrics)


def get_metrics_prometheus() -> str:
    """Export metrics in Prometheus text exposition format."""
    lines: list[str] = []
    for name, value in sorted(_metrics.items()):
        safe_name = name.replace(" ", "_").replace("-", "_")
        lines.append(f"# TYPE gcloud_anomaly_{safe_name} gauge")
        lines.append(f"gcloud_anomaly_{safe_name} {value}")
    return "\n".join(lines) + "\n"


def start_metrics_server(port: int = 9090) -> None:
    """Start a simple HTTP server exposing /metrics endpoint."""
    if not _metrics_enabled:
        logger.info("Metrics not enabled (set METRICS_ENABLED=1)")
        return

    from http.server import BaseHTTPRequestHandler, HTTPServer

    class MetricsHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/metrics":
                body = get_metrics_prometheus().encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:
            logger.debug("Metrics server: %s", format % args)

    server = HTTPServer(("0.0.0.0", port), MetricsHandler)
    logger.info("Metrics server started on port %d", port)
    server.serve_forever()
