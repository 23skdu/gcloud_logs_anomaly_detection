#!/usr/bin/env python3
"""Generate test log events for Google Cloud Logging."""

from __future__ import annotations

import logging
import os

from google.cloud.logging import Client
from google.cloud.logging.handlers import CloudLoggingHandler
from lorem_text import lorem

from gcloud_logs_anomaly_detection.exceptions import GCPAPIError
from gcloud_logs_anomaly_detection.observability import (
    log_metric,
    setup_logging,
    timeit,
)

logger = logging.getLogger("gcloud_anomaly.event_create")


def get_num_events() -> int:
    """Get the number of events to generate from environment."""
    return int(os.getenv("NUMEVENTS", "1000"))


def get_log_name() -> str:
    """Get the log name from environment or use default."""
    return os.getenv("LOG_NAME", "loremipsumevents")


def create_log_client() -> Client:
    """Create and return a Google Cloud Logging client."""
    return Client()


def create_log_handler(client: Client, name: str) -> CloudLoggingHandler:
    """Create and return a Cloud Logging handler."""
    return CloudLoggingHandler(client, name=name)


def setup_logger(handler: CloudLoggingHandler) -> logging.Logger:
    """Set up and return a logger with the given handler."""
    log = logging.getLogger()
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    return log


@timeit
def generate_events(log: logging.Logger, num_events: int) -> None:
    """Generate and log the specified number of events."""
    for _ in range(num_events):
        message = lorem.sentence()
        log.warning(message)
    log_metric("events_generated", num_events)


def main() -> None:
    """Main entry point for generating test log events."""
    setup_logging()
    num_events = get_num_events()
    log_name = get_log_name()

    try:
        client = create_log_client()
        handler = create_log_handler(client, log_name)
        log = setup_logger(handler)
        generate_events(log, num_events)
        client.flush_handlers()
        print(f"Successfully generated {num_events} log events to '{log_name}'.")
    except Exception as exc:
        raise GCPAPIError(f"Failed to generate events: {exc}") from exc


if __name__ == "__main__":
    main()
