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
    @click.option("--store-vector", is_flag=True, help="Store results in Longbow")
    def detect(log_name: str, page_size: int, contamination: str, store_vector: bool) -> None:
        """Detect anomalies in Google Cloud logs."""
        sys.argv = ["gcloud_logs_detect.py"]
        if store_vector:
            os.environ["STORE_VECTOR"] = "1"
        from gcloud_logs_anomaly_detection.detect import main as detect_main

        detect_main()

    @cli.command()
    @click.option("--project-id", envvar="GCP_PROJECT", required=True)
    @click.option("--model-name", envvar="MODEL_NAME", default="gemini-2.0-flash-lite")
    @click.option("--hours-ago", envvar="HOURS_AGO", default=1, type=int)
    @click.option(
        "--backend",
        envvar="LLM_BACKEND",
        default="gemini",
        type=click.Choice(["gemini", "quarrel", "ollama"]),
    )
    def summarize(project_id: str, model_name: str, hours_ago: int, backend: str) -> None:
        """Summarize logs using an LLM."""
        os.environ["LLM_BACKEND"] = backend
        sys.argv = ["gcloud_logs_llmsummary.py"]
        from gcloud_logs_anomaly_detection.llm_summary import main as summary_main

        summary_main()

    @cli.command()
    @click.option("--num-events", envvar="NUMEVENTS", default=1000, type=int)
    @click.option("--log-name", envvar="LOG_NAME", default="loremipsumevents")
    def generate(num_events: int, log_name: str) -> None:
        """Generate test log events in GCP."""
        sys.argv = ["gcloud_event_create.py"]
        from gcloud_logs_anomaly_detection.event_create import main as gen_main

        gen_main()

    @cli.command()
    @click.argument("question")
    @click.option("--model", envvar="MODELNAME", default="smollm2:135m")
    def ask(question: str, model: str) -> None:
        """Ask a question to a local Ollama LLM."""
        sys.argv = ["llmtest.py", question]
        from gcloud_logs_anomaly_detection.llm_test import main as test_main

        test_main()

    @cli.command()
    @click.argument("query", required=False, default=None)
    @click.option(
        "--mode",
        default="dense",
        type=click.Choice(
            ["dense", "sparse", "filtered", "hybrid", "by-id", "temporal", "turboquant"]
        ),
    )
    @click.option("-k", "--top-k", default=10, type=int)
    @click.option("--alpha", default=0.7, type=float, help="Hybrid blending weight")
    @click.option(
        "--filter", "filters", multiple=True,
        help="Metadata filter: KEY=OP:VALUE (e.g. severity=eq:ERROR)",
    )
    @click.option("--duration", default="1h", help="Time window for temporal search")
    @click.option("--id", "vector_id", default=None, type=int, help="Vector ID for by-id search")
    @click.option("--dataset", envvar="LONGBOW_DATASET", default=None)
    def search(
        query: str | None,
        mode: str,
        top_k: int,
        alpha: float,
        filters: tuple[str, ...],
        duration: str,
        vector_id: int | None,
        dataset: str | None,
    ) -> None:
        """Search log vectors in Longbow."""
        from gcloud_logs_anomaly_detection.config import LongbowConfig
        from gcloud_logs_anomaly_detection.longbow_store import (
            search_filtered_logs,
            search_hybrid_logs,
            search_logs_by_id,
            search_similar_logs,
            search_temporal_logs,
            search_turboquant_logs,
        )

        config = LongbowConfig()
        if dataset:
            config.dataset = dataset

        parsed_filters: list[dict[str, str]] = []
        for f in filters:
            key, rest = f.split("=", 1)
            op, value = rest.split(":", 1)
            parsed_filters.append({"field": key, "op": op, "value": value})

        if mode == "temporal":
            df = search_temporal_logs(search_type="sliding_window_time", duration=duration, k=top_k, config=config)
        elif mode == "by-id":
            if vector_id is None:
                click.echo("Error: --id is required for by-id mode", err=True)
                return 1
            df = search_logs_by_id(vector_id, k=top_k, config=config)
        elif mode == "filtered":
            if not query:
                click.echo("Error: query is required for filtered mode", err=True)
                return 1
            df = search_filtered_logs(query, filters=parsed_filters, k=top_k, config=config)
        elif mode == "hybrid":
            if not query:
                click.echo("Error: query is required for hybrid mode", err=True)
                return 1
            df = search_hybrid_logs(query, alpha=alpha, k=top_k, config=config)
        elif mode == "turboquant":
            if not query:
                click.echo("Error: query is required for turboquant mode", err=True)
                return 1
            df = search_turboquant_logs(query, k=top_k, config=config)
        else:
            if not query:
                click.echo("Error: query is required for dense mode", err=True)
                return 1
            df = search_similar_logs(query, k=top_k, config=config)

        click.echo(df.to_string(index=False))

    @cli.command()
    @click.option("--log-name", envvar="LOG_NAME", default="loremipsumevents")
    @click.option("--filter", "log_filter", envvar="LOG_FILTER", default="severity >= INFO")
    @click.option("--hours-ago", envvar="HOURS_AGO", default=24, type=int)
    @click.option("--dataset", envvar="LONGBOW_DATASET", default=None)
    def ingest(log_name: str, log_filter: str, hours_ago: int, dataset: str | None) -> None:
        """Ingest GCP logs into Longbow vector storage."""
        from gcloud_logs_anomaly_detection.config import LongbowConfig
        from gcloud_logs_anomaly_detection.llmsummary import get_log_entries
        from gcloud_logs_anomaly_detection.longbow_store import store_log_entries

        config = LongbowConfig()
        if dataset:
            config.dataset = dataset

        import os

        project_id = os.environ.get("GCP_PROJECT", "")
        if not project_id:
            click.echo("Error: GCP_PROJECT environment variable is required", err=True)
            return 1

        click.echo(f"Fetching logs from project '{project_id}'...")
        entries = get_log_entries(project_id, log_filter, hours_ago=hours_ago)
        click.echo(f"Fetched {len(entries)} log entries.")

        if not entries:
            click.echo("No entries to ingest.")
            return 0

        count = store_log_entries(entries, config=config)
        click.echo(f"Successfully stored {count} vectors in Longbow dataset '{config.dataset}'.")

    cli()
    import os  # noqa: E402
    return 0
