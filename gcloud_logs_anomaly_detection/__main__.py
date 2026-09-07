"""CLI entry point for `python -m gcloud_logs_anomaly_detection`."""

import sys

from gcloud_logs_anomaly_detection.cli import main

if __name__ == "__main__":
    sys.exit(main())
