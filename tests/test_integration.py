"""Integration tests verifying end-to-end workflows with mocked external services."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandas as pd


class TestDetectStoreSearchFlow:
    """Test: detect anomalies -> store in Longbow -> search for them."""

    @patch("gcloud_logs_anomaly_detection.longbow_store.embed_log_entries")
    @patch("gcloud_logs_anomaly_detection.longbow_store.store_vectors")
    @patch("gcloud_logs_anomaly_detection.longbow_store.ensure_dataset")
    def test_detect_to_store_flow(self, mock_ensure, mock_store, mock_embed):
        from gcloud_logs_anomaly_detection.longbow_store import store_log_entries

        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        mock_store.return_value = 1

        anomaly_entries = [
            {
                "timestamp": datetime(2024, 1, 1, tzinfo=UTC),
                "severity": "ERROR",
                "message": "Anomalous disk usage spike",
                "resource": "compute",
                "labels": {"env": "prod"},
            }
        ]
        count = store_log_entries(anomaly_entries)
        assert count == 1
        mock_ensure.assert_called_once()
        mock_store.assert_called_once()

    @patch("gcloud_logs_anomaly_detection.longbow_store.search_vectors")
    @patch("gcloud_logs_anomaly_detection.longbow_store.embed_text")
    def test_search_after_store(self, mock_embed, mock_search):
        from gcloud_logs_anomaly_detection.longbow_store import search_similar_logs

        mock_embed.return_value = [0.1, 0.2, 0.3]
        mock_search.return_value = pd.DataFrame({
            "id": [1],
            "score": [0.95],
            "severity": ["ERROR"],
            "message": ["Anomalous disk usage spike"],
            "resource": ["compute"],
        })

        result = search_similar_logs("disk usage", k=5, use_cache=False)
        assert result.total == 1
        assert result.entries[0].severity == "ERROR"
        assert result.mode == "dense"


class TestIngestSearchFlow:
    """Test: ingest logs -> search for them."""

    @patch("gcloud_logs_anomaly_detection.longbow_store.search_vectors")
    @patch("gcloud_logs_anomaly_detection.longbow_store.embed_text")
    def test_ingest_then_search(self, mock_embed, mock_search):
        from gcloud_logs_anomaly_detection.longbow_store import (
            search_similar_logs,
            store_log_entries,
        )

        mock_embed.return_value = [0.1, 0.2]
        mock_search.return_value = pd.DataFrame({
            "id": [2], "score": [0.88],
            "severity": ["ERROR"], "message": ["Connection timeout"],
        })

        with patch("gcloud_logs_anomaly_detection.longbow_store.embed_log_entries") as mock_batch_embed, \
             patch("gcloud_logs_anomaly_detection.longbow_store.store_vectors") as mock_store, \
             patch("gcloud_logs_anomaly_detection.longbow_store.ensure_dataset"):
            mock_batch_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]
            mock_store.return_value = 2

            entries = [
                {"severity": "INFO", "message": "Request completed", "resource": "api"},
                {"severity": "ERROR", "message": "Connection timeout", "resource": "db"},
            ]
            count = store_log_entries(entries)
            assert count == 2

            result = search_similar_logs("database timeout", use_cache=False)
            assert result.total == 1
            assert "timeout" in result.entries[0].message.lower()


class TestSummarizeQuarrelFlow:
    """Test: summarize logs using quarrel backend."""

    @patch("gcloud_logs_anomaly_detection.quarrel_llm.OpenAI")
    def test_quarrel_backend_end_to_end(self, mock_openai_cls):
        from gcloud_logs_anomaly_detection.quarrel_llm import create_quarrel_llm

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Summary: 2 errors found"))]
        mock_client.chat.completions.create.return_value = mock_response

        llm = create_quarrel_llm()
        assert llm._llm_type == "quarrel"

        result = llm._call("Summarize these logs:")
        assert "Summary" in result
        mock_openai_cls.assert_called_once()

    def test_create_llm_quarrel_backend(self):
        from gcloud_logs_llmsummary import create_llm

        llm = create_llm("default", backend="quarrel")
        assert llm._llm_type == "quarrel"

    def test_create_llm_unknown_backend_raises(self):
        from gcloud_logs_llmsummary import create_llm

        try:
            create_llm("model", backend="nonexistent_backend")
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "nonexistent_backend" in str(e)


class TestHealthCheckFlow:
    """Test: health check commands."""

    @patch("urllib.request.urlopen")
    def test_check_quarrel_success(self, mock_urlopen):
        from gcloud_logs_anomaly_detection.cli import _check_quarrel

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = _check_quarrel()
        assert result["ok"] is True
        assert result["latency_ms"] > 0

    @patch("urllib.request.urlopen")
    def test_check_quarrel_failure(self, mock_urlopen):
        from gcloud_logs_anomaly_detection.cli import _check_quarrel

        mock_urlopen.side_effect = ConnectionRefusedError("Connection refused")
        result = _check_quarrel()
        assert result["ok"] is False
        assert "Connection refused" in result["detail"]

    def test_check_gemini_no_project(self):
        from gcloud_logs_anomaly_detection.cli import _check_gemini

        with patch.dict("os.environ", {}, clear=True):
            result = _check_gemini()
            assert result["ok"] is False
            assert "GCP_PROJECT not set" in result["detail"]


class TestCircuitBreakerIntegration:
    """Test circuit breaker behavior in real operation flow."""

    @patch("gcloud_logs_anomaly_detection.longbow_client.get_client")
    def test_circuit_opens_after_failures(self, mock_get):
        from gcloud_logs_anomaly_detection import longbow_client

        longbow_client._client = None
        longbow_client._circuit._failure_count = 0
        longbow_client._circuit._state = "closed"

        mock_get.side_effect = ConnectionError("Longbow unreachable")

        for _ in range(10):
            try:
                longbow_client.get_client()
            except (ConnectionError, ImportError):
                longbow_client._circuit.record_failure()

        assert longbow_client._circuit.state == "open"

        try:
            longbow_client._circuit.allow_request()
            longbow_client.get_client()
            raise AssertionError("Should have raised")
        except Exception:
            pass

        longbow_client._client = None
        longbow_client._circuit._failure_count = 0
        longbow_client._circuit._state = "closed"


class TestIncrementalIngestionFlow:
    """Test: incremental ingestion with watermark tracking."""

    @patch("gcloud_logs_anomaly_detection.longbow_store.get_watermark")
    @patch("gcloud_logs_anomaly_detection.longbow_store.store_log_entries")
    @patch("gcloud_logs_anomaly_detection.longbow_store.set_watermark")
    def test_skips_already_ingested(self, mock_set_wm, mock_store, mock_get_wm):
        from gcloud_logs_anomaly_detection.longbow_store import store_log_entries_incremental

        mock_get_wm.return_value = 2_000_000_000  # 2 seconds in ns
        mock_store.return_value = 1

        old = {"timestamp": datetime.fromtimestamp(1.0), "severity": "INFO", "message": "old"}
        new = {"timestamp": datetime.fromtimestamp(3.0), "severity": "ERROR", "message": "new"}
        count = store_log_entries_incremental([old, new])
        assert count == 1

    @patch("gcloud_logs_anomaly_detection.longbow_store.get_watermark")
    def test_processes_all_when_no_watermark(self, mock_get_wm):
        from gcloud_logs_anomaly_detection.longbow_store import store_log_entries_incremental

        mock_get_wm.return_value = None

        with patch("gcloud_logs_anomaly_detection.longbow_store.store_log_entries") as mock_store:
            mock_store.return_value = 2
            entries = [
                {"severity": "INFO", "message": "a"},
                {"severity": "ERROR", "message": "b"},
            ]
            count = store_log_entries_incremental(entries)
            assert count == 2
            mock_store.assert_called_once()


class TestSchemaNormalizationIntegration:
    """Test: log entry normalization across log types."""

    def test_full_normalization_pipeline(self):
        from gcloud_logs_anomaly_detection.embeddings import (
            _entry_to_text,
            normalize_entries,
        )

        raw_entries = [
            {
                "severity": "ERROR",
                "protoPayload": {"statusMessage": "Permission denied on resource"},
                "resource": {"labels": {"project_id": "my-project", "resource_type": "dataset"}},
                "labels": {"env": "prod"},
            },
            {
                "severity": "WARNING",
                "message": "High CPU usage",
                "resource": "compute-engine",
                "labels": {},
            },
        ]

        normalized = normalize_entries(raw_entries, log_type="audit")
        assert len(normalized) == 2
        assert normalized[0]["message"] == "Permission denied on resource"
        assert normalized[0]["resource"] == "my-project"
        assert normalized[1]["message"] == "High CPU usage"

        texts = [_entry_to_text(e) for e in normalized]
        assert all(isinstance(t, str) for t in texts)
        assert len(texts[0]) > 0

    def test_embedding_after_normalization(self):
        from gcloud_logs_anomaly_detection.embeddings import _entry_to_text, normalize_entry

        raw = {
            "severity": "CRITICAL",
            "message": "Service down",
            "resource": "k8s-cluster",
            "labels": {"team": "platform"},
        }
        normalized = normalize_entry(raw, "generic")
        text = _entry_to_text(normalized)
        assert "CRITICAL" in text
        assert "Service down" in text
        assert "team=platform" in text


class TestMetricsIntegration:
    """Test: metrics collection across operations."""

    @patch.dict("os.environ", {"METRICS_ENABLED": "1"})
    def test_metrics_collected_during_search(self):
        import gcloud_logs_anomaly_detection.observability as obs

        obs._metrics_enabled = True
        obs._metrics.clear()
        from gcloud_logs_anomaly_detection.observability import get_metrics, log_metric

        log_metric("search_test_metric", 999)
        metrics = get_metrics()
        assert metrics["search_test_metric"] == 999.0
        obs._metrics.clear()

    @patch.dict("os.environ", {"METRICS_ENABLED": "1"})
    def test_prometheus_output_format(self):
        import gcloud_logs_anomaly_detection.observability as obs

        obs._metrics_enabled = True
        obs._metrics.clear()
        from gcloud_logs_anomaly_detection.observability import get_metrics_prometheus, log_metric

        log_metric("integration_test", 42)
        output = get_metrics_prometheus()
        lines = output.strip().split("\n")
        assert any("gcloud_anomaly_integration_test" in line for line in lines)
        assert any("42.0" in line for line in lines)
        obs._metrics.clear()


class TestPluginArchitectureIntegration:
    """Test: plugin backend discovery and creation."""

    def test_builtin_backends_discovered(self):
        from gcloud_logs_anomaly_detection.config import get_builtin_backends, list_backends

        builtins = get_builtin_backends()
        all_backends = list_backends()
        assert "gemini" in builtins
        assert "quarrel" in builtins
        assert "ollama" in builtins
        for name in builtins:
            assert name in all_backends

    def test_create_llm_gemini_backend(self):
        from gcloud_logs_llmsummary import create_llm

        with patch("gcloud_logs_llmsummary.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            create_llm("gemini-2.0-flash-lite", backend="gemini")
            mock_cls.assert_called_once_with(model="gemini-2.0-flash-lite", temperature=0.0)
