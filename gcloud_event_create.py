#!/usr/bin/env python3
"""Generate test log events for Google Cloud Logging."""

import logging
import os
from typing import Optional

from google.cloud.logging import Client
from google.cloud.logging.handlers import CloudLoggingHandler
from lorem_text import lorem


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
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def generate_events(logger: logging.Logger, num_events: int) -> None:
    """Generate and log the specified number of events."""
    for i in range(num_events):
        message = lorem.sentence()
        logger.warning(message)


def main() -> None:
    """Main entry point for generating test log events."""
    num_events = get_num_events()
    log_name = get_log_name()

    client = create_log_client()
    handler = create_log_handler(client, log_name)
    logger = setup_logger(handler)

    generate_events(logger, num_events)
    client.flush_handlers()
    print(f"Successfully generated {num_events} log events to '{log_name}'.")


if __name__ == "__main__":
    main()
