"""Tests for Longbow vector storage operations."""

import time
from unittest.mock import MagicMock, patch

import pandas as pd

from gcloud_logs_anomaly_detection.config import LongbowConfig


class TestLongbowConfig:
    def test_defaults(self):
        config = LongbowConfig()
        assert config.uri == "grpc://localhost:3000"
        assert config.meta_uri == "grpc://localhost:3001"
        assert config.dataset == "gcloud_logs"
        assert config.dims == 384
        assert config.data_type == "float32"
        assert config.search_k == 10
        assert config.search_alpha == 0.7
        assert config.embedding_model == "all-MiniLM-L6-v2"


class TestCircuitBreaker:
    def test_closed_by_default(self):
        from gcloud_logs_anomaly_detection.longbow_client import CircuitBreaker

        cb = CircuitBreaker()
        assert cb.state == "closed"
        assert cb.allow_request() is True

    def test_opens_after_threshold(self):
        from gcloud_logs_anomaly_detection.longbow_client import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=60)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"
        assert cb.allow_request() is False

    def test_half_open_after_cooldown(self):
        from gcloud_logs_anomaly_detection.longbow_client import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        time.sleep(0.15)
        assert cb.state == "half_open"
        assert cb.allow_request() is True

    def test_closes_on_success_from_half_open(self):
        from gcloud_logs_anomaly_detection.longbow_client import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=2, cooldown_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == "half_open"
        cb.record_success()
        assert cb.state == "closed"

    def test_resets_failure_count_on_success(self):
        from gcloud_logs_anomaly_detection.longbow_client import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0
        assert cb.state == "closed"


class TestLongbowStore:
    @patch("gcloud_logs_anomaly_detection.longbow_store.embed_log_entries")
    @patch("gcloud_logs_anomaly_detection.longbow_store.store_vectors")
    @patch("gcloud_logs_anomaly_detection.longbow_store.ensure_dataset")
    def test_store_log_entries(self, mock_ensure, mock_store, mock_embed):
        mock_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_store.return_value = 2

        from gcloud_logs_anomaly_detection.longbow_store import store_log_entries

        entries = [
            {"severity": "ERROR", "message": "a", "resource": "r1"},
            {"severity": "WARN", "message": "b", "resource": "r2"},
        ]
        count = store_log_entries(entries)
        assert count == 2
        mock_ensure.assert_called_once()
        mock_store.assert_called_once()

    def test_store_log_entries_empty(self):
        from gcloud_logs_anomaly_detection.longbow_store import store_log_entries

        count = store_log_entries([])
        assert count == 0

    @patch("gcloud_logs_anomaly_detection.longbow_store.search_vectors")
    @patch("gcloud_logs_anomaly_detection.longbow_store.embed_text")
    def test_search_similar_logs(self, mock_embed, mock_search):
        mock_embed.return_value = [0.1, 0.2]
        mock_df = pd.DataFrame({"id": [1], "score": [0.9]})
        mock_search.return_value = mock_df

        from gcloud_logs_anomaly_detection.longbow_store import search_similar_logs

        result = search_similar_logs("error logs", use_cache=False)
        assert hasattr(result, "entries")
        assert result.mode == "dense"
        assert result.total == 1
        mock_embed.assert_called_once()
        mock_search.assert_called_once()

    @patch("gcloud_logs_anomaly_detection.longbow_store.search_filtered")
    @patch("gcloud_logs_anomaly_detection.longbow_store.embed_text")
    def test_search_filtered_logs(self, mock_embed, mock_search):
        mock_embed.return_value = [0.1, 0.2]
        mock_search.return_value = pd.DataFrame({"id": [1]})

        from gcloud_logs_anomaly_detection.longbow_store import search_filtered_logs

        filters = [{"field": "severity", "op": "eq", "value": "ERROR"}]
        result = search_filtered_logs("test", filters=filters)
        assert result.mode == "filtered"
        mock_search.assert_called_once()

    @patch("gcloud_logs_anomaly_detection.longbow_store.search_temporal")
    def test_search_temporal_logs(self, mock_search):
        mock_search.return_value = pd.DataFrame({"id": [1]})

        from gcloud_logs_anomaly_detection.longbow_store import search_temporal_logs

        result = search_temporal_logs(duration="1h")
        assert result.mode == "temporal"
        mock_search.assert_called_once()

    @patch("gcloud_logs_anomaly_detection.longbow_store.search_by_id")
    def test_search_logs_by_id(self, mock_search):
        mock_search.return_value = pd.DataFrame({"id": [1]})

        from gcloud_logs_anomaly_detection.longbow_store import search_logs_by_id

        result = search_logs_by_id(12345)
        assert result.mode == "by-id"
        mock_search.assert_called_once()

    @patch("gcloud_logs_anomaly_detection.longbow_store.search_turboquant")
    @patch("gcloud_logs_anomaly_detection.longbow_store.embed_text")
    def test_search_turboquant_logs(self, mock_embed, mock_search):
        mock_embed.return_value = [0.1, 0.2]
        mock_search.return_value = pd.DataFrame({"id": [1]})

        from gcloud_logs_anomaly_detection.longbow_store import search_turboquant_logs

        result = search_turboquant_logs("test")
        assert result.mode == "turboquant"
        mock_search.assert_called_once()


class TestSearchResult:
    def test_to_json(self):
        from gcloud_logs_anomaly_detection.longbow_store import LogEntry, SearchResult

        result = SearchResult(
            entries=[LogEntry(id=1, score=0.9, timestamp="2024-01-01", severity="ERROR", message="test", resource="res")],
            total=1,
            query_time_ms=12.5,
            mode="dense",
        )
        import json
        data = json.loads(result.to_json())
        assert data["total"] == 1
        assert data["mode"] == "dense"
        assert len(data["entries"]) == 1

    def test_to_csv(self):
        from gcloud_logs_anomaly_detection.longbow_store import LogEntry, SearchResult

        result = SearchResult(
            entries=[LogEntry(id=1, score=0.9, timestamp="2024-01-01", severity="ERROR", message="test", resource="res")],
            total=1,
            query_time_ms=12.5,
            mode="dense",
        )
        csv = result.to_csv()
        assert "id,score" in csv
        assert "1,0.9" in csv

    def test_to_csv_empty(self):
        from gcloud_logs_anomaly_detection.longbow_store import SearchResult

        result = SearchResult(entries=[], total=0, query_time_ms=0, mode="dense")
        assert result.to_csv() == ""


class TestSearchCache:
    def test_cache_set_and_get(self):
        from gcloud_logs_anomaly_detection.longbow_store import _cache_key, _get_cached, _set_cached

        key = _cache_key("test", "dense", k=10)
        _set_cached(key, "cached_result")
        assert _get_cached(key) == "cached_result"

    def test_cache_miss(self):
        from gcloud_logs_anomaly_detection.longbow_store import _get_cached

        assert _get_cached("nonexistent_key") is None

    def test_invalidate_cache(self):
        from gcloud_logs_anomaly_detection.longbow_store import (
            _cache_key,
            _get_cached,
            _set_cached,
            invalidate_cache,
        )

        key = _cache_key("test", "dense")
        _set_cached(key, "result")
        invalidate_cache()
        assert _get_cached(key) is None


class TestAsyncIngestion:
    @patch("gcloud_logs_anomaly_detection.longbow_store.embed_log_entries")
    @patch("gcloud_logs_anomaly_detection.longbow_store.store_vectors")
    @patch("gcloud_logs_anomaly_detection.longbow_store.ensure_dataset")
    def test_store_log_entries_async(self, mock_ensure, mock_store, mock_embed):
        mock_embed.return_value = [[0.1], [0.2]]
        mock_store.return_value = 1

        from gcloud_logs_anomaly_detection.longbow_store import store_log_entries_async

        entries = [{"severity": "ERROR", "message": "a"}, {"severity": "WARN", "message": "b"}]
        count = store_log_entries_async(entries, batch_size=2, max_workers=1)
        assert count == 1

    def test_store_log_entries_async_empty(self):
        from gcloud_logs_anomaly_detection.longbow_store import store_log_entries_async

        count = store_log_entries_async([])
        assert count == 0


class TestWatermark:
    @patch("gcloud_logs_anomaly_detection.longbow_store.get_watermark")
    @patch("gcloud_logs_anomaly_detection.longbow_store.store_log_entries")
    @patch("gcloud_logs_anomaly_detection.longbow_store.set_watermark")
    def test_incremental_filters_old_entries(self, mock_set_wm, mock_store, mock_get_wm):
        mock_get_wm.return_value = 1_000_000_000  # 1 second in ns
        mock_store.return_value = 1

        from datetime import datetime

        from gcloud_logs_anomaly_detection.longbow_store import store_log_entries_incremental

        old_entry = {"timestamp": datetime.fromtimestamp(0.5), "severity": "ERROR", "message": "old"}
        new_entry = {"timestamp": datetime.fromtimestamp(2.0), "severity": "ERROR", "message": "new"}
        count = store_log_entries_incremental([old_entry, new_entry])
        assert count == 1
        mock_store.assert_called_once()

    @patch("gcloud_logs_anomaly_detection.longbow_store.get_watermark")
    def test_incremental_no_entries_when_all_old(self, mock_get_wm):
        mock_get_wm.return_value = 9999999999999

        from datetime import datetime

        from gcloud_logs_anomaly_detection.longbow_store import store_log_entries_incremental

        old_entry = {"timestamp": datetime.fromtimestamp(1.0), "severity": "ERROR", "message": "old"}
        count = store_log_entries_incremental([old_entry])
        assert count == 0


class TestSchemaNormalization:
    def test_normalize_generic_entry(self):
        from gcloud_logs_anomaly_detection.embeddings import normalize_entry

        raw = {
            "severity": "ERROR",
            "message": "Disk full",
            "resource": "compute",
            "labels": {"env": "prod"},
            "timestamp": "2024-01-01T00:00:00Z",
        }
        result = normalize_entry(raw, "generic")
        assert result["severity"] == "ERROR"
        assert result["message"] == "Disk full"
        assert result["resource"] == "compute"
        assert result["labels"] == {"env": "prod"}

    def test_normalize_audit_entry(self):
        from gcloud_logs_anomaly_detection.embeddings import normalize_entry

        raw = {
            "severity": "INFO",
            "protoPayload": {"statusMessage": "permission denied"},
            "resource": {"labels": {"project_id": "my-project"}},
        }
        result = normalize_entry(raw, "audit")
        assert result["message"] == "permission denied"
        assert result["resource"] == "my-project"

    def test_normalize_entries_batch(self):
        from gcloud_logs_anomaly_detection.embeddings import normalize_entries

        entries = [
            {"severity": "ERROR", "message": "a", "resource": "r1"},
            {"severity": "WARN", "message": "b", "resource": "r2"},
        ]
        result = normalize_entries(entries)
        assert len(result) == 2
        assert result[0]["severity"] == "ERROR"

    def test_entry_to_text_with_dict_labels(self):
        from gcloud_logs_anomaly_detection.embeddings import _entry_to_text

        entry = {"severity": "ERROR", "message": "test", "resource": "res", "labels": {"env": "prod"}}
        result = _entry_to_text(entry)
        assert "env=prod" in result

    def test_entry_to_text_with_string_labels(self):
        from gcloud_logs_anomaly_detection.embeddings import _entry_to_text

        entry = {"severity": "ERROR", "message": "test", "resource": "res", "labels": '{"env": "prod"}'}
        result = _entry_to_text(entry)
        assert "env" in result


class TestMetricsExport:
    @patch.dict("os.environ", {"METRICS_ENABLED": "1"})
    def test_log_metric_collects(self):
        import gcloud_logs_anomaly_detection.observability as obs

        obs._metrics_enabled = True
        obs._metrics.clear()
        from gcloud_logs_anomaly_detection.observability import get_metrics, log_metric

        log_metric("test_metric", 42)
        metrics = get_metrics()
        assert metrics["test_metric"] == 42.0
        obs._metrics.clear()

    @patch.dict("os.environ", {"METRICS_ENABLED": "1"})
    def test_prometheus_format(self):
        import gcloud_logs_anomaly_detection.observability as obs

        obs._metrics_enabled = True
        obs._metrics.clear()
        from gcloud_logs_anomaly_detection.observability import get_metrics_prometheus, log_metric

        log_metric("test_counter", 100)
        output = get_metrics_prometheus()
        assert "gcloud_anomaly_test_counter" in output
        assert "100.0" in output
        obs._metrics.clear()

    def test_metrics_empty(self):
        from gcloud_logs_anomaly_detection.observability import get_metrics_prometheus

        output = get_metrics_prometheus()
        assert output == "" or output.strip() == ""


class TestPluginBackends:
    def test_list_backends(self):
        from gcloud_logs_anomaly_detection.config import list_backends

        backends = list_backends()
        assert "gemini" in backends
        assert "quarrel" in backends
        assert "ollama" in backends

    def test_get_builtin_backends(self):
        from gcloud_logs_anomaly_detection.config import get_builtin_backends

        backends = get_builtin_backends()
        assert len(backends) == 3


class TestLongbowClient:
    @patch("gcloud_logs_anomaly_detection.longbow_client.get_client")
    def test_get_client_creates_once(self, mock_get):
        mock_client = MagicMock()
        mock_get.return_value = mock_client

        from gcloud_logs_anomaly_detection import longbow_client

        longbow_client._client = None
        longbow_client.get_client()
        mock_get.assert_called_once()
        longbow_client._client = None

    def test_disconnect(self):
        from gcloud_logs_anomaly_detection import longbow_client

        longbow_client._client = MagicMock()
        longbow_client.disconnect()
        assert longbow_client._client is None

    @patch("gcloud_logs_anomaly_detection.longbow_client.get_client")
    def test_ensure_dataset(self, mock_get):
        mock_client = MagicMock()
        mock_get.return_value = mock_client

        from gcloud_logs_anomaly_detection.longbow_client import ensure_dataset

        ensure_dataset()
        mock_client.create_namespace.assert_called_once()
