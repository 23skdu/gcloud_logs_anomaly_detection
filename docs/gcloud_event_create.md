# Google Cloud Log Event Generator

This script (gcloud_event_create.py) generates synthetic log events and sends
them to Google Cloud Logging.

## Features

- Uses lorem-text to generate random log messages.
- Sends logs to a specified Google Cloud Logging log name.
- Configurable number of events via environment variables.

## Configuration

- NUMEVENTS: Number of events to generate (default: 1000).
- LOG_NAME: Name of the log to write to (default: 'loremipsumevents').
