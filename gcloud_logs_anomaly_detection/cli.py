"""Unified CLI entry point using click."""

from __future__ import annotations

import sys

try:
    import click
except ImportError:
    click = None  # type: ignore[assignment]


def _has_click() -> bool:
    return click is not None


def main() -> int:
    """Main CLI dispatcher. Falls back to individual script entry points."""
    if not _has_click():
        print("Install click for unified CLI: pip install click", file=sys.stderr)
        return 1

    @click.group()
    @click.version_option(package_name="gcloud-logs-anomaly-detection")
    def cli() -> None:
        """gcloud-logs-anomaly-detection: ML-powered log anomaly detection."""

    @cli.command()
    @click.option("--log-name", envvar="LOG_NAME", default="loremipsumevents")
    @click.option("--page-size", envvar="LOG_PAGE_SIZE", default=10000, type=int)
    @click.option("--contamination", envvar="LOG_CONTAMINATION", default="auto")
    def detect(log_name: str, page_size: int, contamination: str) -> None:
        """Detect anomalies in Google Cloud logs."""
        from gcloud_logs_anomaly_detection.detect import main as detect_main

        sys.argv = ["gcloud_logs_detect.py"]
        detect_main()

    @cli.command()
    @click.option("--project-id", envvar="GCP_PROJECT", required=True)
    @click.option("--model-name", envvar="MODEL_NAME", default="gemini-2.0-flash-lite")
    @click.option("--hours-ago", envvar="HOURS_AGO", default=1, type=int)
    def summarize(project_id: str, model_name: str, hours_ago: int) -> None:
        """Summarize logs using an LLM."""
        from gcloud_logs_anomaly_detection.llm_summary import main as summary_main

        sys.argv = ["gcloud_logs_llmsummary.py"]
        summary_main()

    @cli.command()
    @click.option("--num-events", envvar="NUMEVENTS", default=1000, type=int)
    @click.option("--log-name", envvar="LOG_NAME", default="loremipsumevents")
    def generate(num_events: int, log_name: str) -> None:
        """Generate test log events in GCP."""
        from gcloud_logs_anomaly_detection.event_create import main as gen_main

        sys.argv = ["gcloud_event_create.py"]
        gen_main()

    @cli.command()
    @click.argument("question")
    @click.option("--model", envvar="MODELNAME", default="smollm2:135m")
    def ask(question: str, model: str) -> None:
        """Ask a question to a local Ollama LLM."""
        from gcloud_logs_anomaly_detection.llm_test import main as test_main

        sys.argv = ["llmtest.py", question]
        test_main()

    cli()
    return 0
