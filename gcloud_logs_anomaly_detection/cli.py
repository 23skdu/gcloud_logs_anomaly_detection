"""Unified CLI entry point using click."""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

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
        os.environ["LOG_NAME"] = log_name
        os.environ["LOG_PAGE_SIZE"] = str(page_size)
        os.environ["LOG_CONTAMINATION"] = contamination
        if store_vector:
            os.environ["STORE_VECTOR"] = "1"
        from gcloud_logs_detect import main as detect_main

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
        os.environ["GCP_PROJECT"] = project_id
        os.environ["MODEL_NAME"] = model_name
        os.environ["HOURS_AGO"] = str(hours_ago)
        os.environ["LLM_BACKEND"] = backend
        from gcloud_logs_llmsummary import main as summary_main

        summary_main()

    @cli.command()
    @click.option("--num-events", envvar="NUMEVENTS", default=1000, type=int)
    @click.option("--log-name", envvar="LOG_NAME", default="loremipsumevents")
    def generate(num_events: int, log_name: str) -> None:
        """Generate test log events in GCP."""
        os.environ["NUMEVENTS"] = str(num_events)
        os.environ["LOG_NAME"] = log_name
        from gcloud_event_create import main as gen_main

        gen_main()

    @cli.command()
    @click.argument("question")
    @click.option("--model", envvar="MODELNAME", default="smollm2:135m")
    def ask(question: str, model: str) -> None:
        """Ask a question to a local Ollama LLM."""
        os.environ["MODELNAME"] = model
        sys.argv = ["llmtest.py", question]
        from llmtest import main as test_main

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
    @click.option(
        "--format", "output_format",
        default="table",
        type=click.Choice(["table", "json", "csv"]),
        help="Output format",
    )
    @click.option("--no-cache", is_flag=True, help="Skip search result cache")
    def search(
        query: str | None,
        mode: str,
        top_k: int,
        alpha: float,
        filters: tuple[str, ...],
        duration: str,
        vector_id: int | None,
        dataset: str | None,
        output_format: str,
        no_cache: bool,
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

        result: Any = None

        if mode == "temporal":
            result = search_temporal_logs(search_type="sliding_window_time", duration=duration, k=top_k, config=config)
        elif mode == "by-id":
            if vector_id is None:
                click.echo("Error: --id is required for by-id mode", err=True)
                sys.exit(1)
            result = search_logs_by_id(vector_id, k=top_k, config=config)
        elif mode == "filtered":
            if not query:
                click.echo("Error: query is required for filtered mode", err=True)
                sys.exit(1)
            result = search_filtered_logs(query, filters=parsed_filters, k=top_k, config=config)
        elif mode == "hybrid":
            if not query:
                click.echo("Error: query is required for hybrid mode", err=True)
                sys.exit(1)
            result = search_hybrid_logs(query, alpha=alpha, k=top_k, config=config)
        elif mode == "turboquant":
            if not query:
                click.echo("Error: query is required for turboquant mode", err=True)
                sys.exit(1)
            result = search_turboquant_logs(query, k=top_k, config=config)
        else:
            if not query:
                click.echo("Error: query is required for dense mode", err=True)
                sys.exit(1)
            result = search_similar_logs(query, k=top_k, config=config)

        if output_format == "json":
            if hasattr(result, "to_json"):
                click.echo(result.to_json())
            else:
                click.echo(json.dumps(str(result)))
        elif output_format == "csv":
            if hasattr(result, "to_csv"):
                click.echo(result.to_csv())
            else:
                click.echo(str(result))
        else:
            if hasattr(result, "entries"):
                for entry in result.entries:
                    click.echo(
                        f"[{entry.id}] score={entry.score:.4f} "
                        f"severity={entry.severity} resource={entry.resource} "
                        f"message={entry.message[:80]}"
                    )
                click.echo(f"\n({result.total} results in {result.query_time_ms:.1f}ms)")
            else:
                click.echo(str(result))

    @cli.command()
    @click.option("--log-name", envvar="LOG_NAME", default="loremipsumevents")
    @click.option("--filter", "log_filter", envvar="LOG_FILTER", default="severity >= INFO")
    @click.option("--hours-ago", envvar="HOURS_AGO", default=24, type=int)
    @click.option("--dataset", envvar="LONGBOW_DATASET", default=None)
    @click.option("--async", "use_async", is_flag=True, help="Use concurrent batch ingestion")
    @click.option("--workers", default=4, type=int, help="Worker threads for async mode")
    @click.option("--incremental", is_flag=True, help="Skip already-ingested entries (watermark)")
    def ingest(
        log_name: str,
        log_filter: str,
        hours_ago: int,
        dataset: str | None,
        use_async: bool,
        workers: int,
        incremental: bool,
    ) -> None:
        """Ingest GCP logs into Longbow vector storage."""
        from gcloud_logs_anomaly_detection.config import LongbowConfig
        from gcloud_logs_anomaly_detection.longbow_store import (
            store_log_entries,
            store_log_entries_async,
            store_log_entries_incremental,
        )
        from gcloud_logs_llmsummary import get_log_entries

        config = LongbowConfig()
        if dataset:
            config.dataset = dataset

        project_id = os.environ.get("GCP_PROJECT", "")
        if not project_id:
            click.echo("Error: GCP_PROJECT environment variable is required", err=True)
            sys.exit(1)

        click.echo(f"Fetching logs from project '{project_id}'...")
        entries = get_log_entries(project_id, log_filter, hours_ago=hours_ago)
        click.echo(f"Fetched {len(entries)} log entries.")

        if not entries:
            click.echo("No entries to ingest.")
            return

        start = time.monotonic()
        if incremental:
            count = store_log_entries_incremental(entries, config=config)
        elif use_async:
            count = store_log_entries_async(entries, config=config, max_workers=workers)
        else:
            count = store_log_entries(entries, config=config)
        elapsed = time.monotonic() - start

        click.echo(f"Stored {count} vectors in Longbow dataset '{config.dataset}' ({elapsed:.2f}s).")

    @cli.command()
    @click.option("--longbow", is_flag=True, help="Check Longbow connectivity")
    @click.option("--quarrel", is_flag=True, help="Check Quarrel connectivity")
    @click.option("--gemini", is_flag=True, help="Check Gemini/GCP credentials")
    @click.option("--all", "check_all", is_flag=True, help="Check all services")
    def health(longbow: bool, quarrel: bool, gemini: bool, check_all: bool) -> None:
        """Check connectivity to all configured services."""
        if not any([longbow, quarrel, gemini, check_all]):
            check_all = True

        results: dict[str, dict[str, Any]] = {}

        if check_all or longbow:
            results["longbow"] = _check_longbow()
        if check_all or quarrel:
            results["quarrel"] = _check_quarrel()
        if check_all or gemini:
            results["gemini"] = _check_gemini()

        all_healthy = True
        for service, info in results.items():
            status = "healthy" if info["ok"] else "unhealthy"
            latency = info.get("latency_ms", 0)
            detail = info.get("detail", "")
            symbol = "+" if info["ok"] else "x"
            line = f"[{symbol}] {service}: {status}"
            if latency:
                line += f" ({latency:.0f}ms)"
            if detail:
                line += f" - {detail}"
            click.echo(line)
            if not info["ok"]:
                all_healthy = False

        sys.exit(0 if all_healthy else 1)

    @cli.command()
    def backends() -> None:
        """List available LLM backends."""
        from gcloud_logs_anomaly_detection.config import list_backends

        available = list_backends()
        for name, ep in sorted(available.items()):
            click.echo(f"  {name:12s}  {ep}")
        click.echo(f"\n{len(available)} backend(s) available.")

    cli()
    return 0


def _check_longbow() -> dict[str, Any]:
    """Check Longbow gRPC connectivity."""
    start = time.monotonic()
    try:
        from gcloud_logs_anomaly_detection.config import LongbowConfig
        from gcloud_logs_anomaly_detection.longbow_client import get_client

        config = LongbowConfig()
        get_client(config)
        elapsed = (time.monotonic() - start) * 1000
        return {"ok": True, "latency_ms": elapsed, "detail": config.uri}
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        return {"ok": False, "latency_ms": elapsed, "detail": str(exc)}


def _check_quarrel() -> dict[str, Any]:
    """Check Quarrel HTTP health endpoint."""
    start = time.monotonic()
    try:
        import urllib.error
        import urllib.request

        from gcloud_logs_anomaly_detection.config import QuarrelConfig

        config = QuarrelConfig()
        url = f"{config.base_url}/health"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            elapsed = (time.monotonic() - start) * 1000
            return {"ok": resp.status == 200, "latency_ms": elapsed, "detail": config.base_url}
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        return {"ok": False, "latency_ms": elapsed, "detail": str(exc)}


def _check_gemini() -> dict[str, Any]:
    """Check GCP credentials and Gemini model access."""
    start = time.monotonic()
    try:
        project_id = os.environ.get("GCP_PROJECT", "")
        if not project_id:
            return {"ok": False, "latency_ms": 0, "detail": "GCP_PROJECT not set"}
        from google.cloud import logging as gcp_logging
        client = gcp_logging.Client(project=project_id)
        client.list_entries(max_results=1)
        elapsed = (time.monotonic() - start) * 1000
        return {"ok": True, "latency_ms": elapsed, "detail": project_id}
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        return {"ok": False, "latency_ms": elapsed, "detail": str(exc)}
