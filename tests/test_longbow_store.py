"""Tests for Longbow vector storage operations."""

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
    @patch("gcloud_logs_anomaly_detection.embeddings.embed_text")
    def test_search_similar_logs(self, mock_embed, mock_search):
        mock_embed.return_value = [0.1, 0.2]
        mock_df = pd.DataFrame({"id": [1], "score": [0.9]})
        mock_search.return_value = mock_df

        from gcloud_logs_anomaly_detection.longbow_store import search_similar_logs

        search_similar_logs("error logs")
        mock_embed.assert_called_once()
        mock_search.assert_called_once()

    @patch("gcloud_logs_anomaly_detection.longbow_store.search_filtered")
    @patch("gcloud_logs_anomaly_detection.embeddings.embed_text")
    def test_search_filtered_logs(self, mock_embed, mock_search):
        mock_embed.return_value = [0.1, 0.2]
        mock_search.return_value = pd.DataFrame({"id": [1]})

        from gcloud_logs_anomaly_detection.longbow_store import search_filtered_logs

        filters = [{"field": "severity", "op": "eq", "value": "ERROR"}]
        search_filtered_logs("test", filters=filters)
        mock_search.assert_called_once()

    @patch("gcloud_logs_anomaly_detection.longbow_store.search_temporal")
    def test_search_temporal_logs(self, mock_search):
        mock_search.return_value = pd.DataFrame({"id": [1]})

        from gcloud_logs_anomaly_detection.longbow_store import search_temporal_logs

        search_temporal_logs(duration="1h")
        mock_search.assert_called_once()

    @patch("gcloud_logs_anomaly_detection.longbow_store.search_by_id")
    def test_search_logs_by_id(self, mock_search):
        mock_search.return_value = pd.DataFrame({"id": [1]})

        from gcloud_logs_anomaly_detection.longbow_store import search_logs_by_id

        search_logs_by_id(12345)
        mock_search.assert_called_once()

    @patch("gcloud_logs_anomaly_detection.longbow_store.search_turboquant")
    @patch("gcloud_logs_anomaly_detection.embeddings.embed_text")
    def test_search_turboquant_logs(self, mock_embed, mock_search):
        mock_embed.return_value = [0.1, 0.2]
        mock_search.return_value = pd.DataFrame({"id": [1]})

        from gcloud_logs_anomaly_detection.longbow_store import search_turboquant_logs

        search_turboquant_logs("test")
        mock_search.assert_called_once()


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
