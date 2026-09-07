"""Tests for embedding utilities."""

from unittest.mock import MagicMock, patch

from gcloud_logs_anomaly_detection import embeddings


class TestEmbeddings:
    def test_entry_to_text(self):
        from gcloud_logs_anomaly_detection.embeddings import _entry_to_text

        entry = {
            "severity": "ERROR",
            "message": "Disk full",
            "resource": "compute",
            "labels": {"env": "prod"},
        }
        result = _entry_to_text(entry)
        assert "ERROR" in result
        assert "Disk full" in result
        assert "compute" in result

    def test_entry_to_text_missing_fields(self):
        from gcloud_logs_anomaly_detection.embeddings import _entry_to_text

        result = _entry_to_text({})
        assert isinstance(result, str)

    def test_entry_to_text_uses_payload(self):
        from gcloud_logs_anomaly_detection.embeddings import _entry_to_text

        entry = {"severity": "WARN", "payload": "CPU spike"}
        result = _entry_to_text(entry)
        assert "CPU spike" in result

    @patch("gcloud_logs_anomaly_detection.embeddings.get_model")
    def test_embed_text(self, mock_get_model):
        mock_model = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]
        mock_get_model.return_value = mock_model

        from gcloud_logs_anomaly_detection.embeddings import embed_text

        result = embed_text("test text")
        assert result == [0.1, 0.2, 0.3]
        mock_model.encode.assert_called_once_with("test text")

    @patch("gcloud_logs_anomaly_detection.embeddings.get_model")
    def test_embed_log_entry(self, mock_get_model):
        mock_model = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [0.1, 0.2]
        mock_get_model.return_value = mock_model

        from gcloud_logs_anomaly_detection.embeddings import embed_log_entry

        entry = {"severity": "ERROR", "message": "test", "resource": "res"}
        result = embed_log_entry(entry)
        assert result == [0.1, 0.2]

    @patch("gcloud_logs_anomaly_detection.embeddings.get_model")
    def test_embed_log_entries(self, mock_get_model):
        mock_model = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [[0.1], [0.2]]
        mock_get_model.return_value = mock_model

        from gcloud_logs_anomaly_detection.embeddings import embed_log_entries

        entries = [
            {"severity": "ERROR", "message": "a"},
            {"severity": "WARN", "message": "b"},
        ]
        result = embed_log_entries(entries)
        assert len(result) == 2

    def test_embed_log_entries_empty(self):
        from gcloud_logs_anomaly_detection.embeddings import embed_log_entries

        result = embed_log_entries([])
        assert result == []

    def test_get_model_caches(self):
        embeddings._model = None
        mock_instance = MagicMock()

        original_get = embeddings.get_model

        call_count = 0

        def fake_get(model_name: str) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                embeddings._model = mock_instance
            return embeddings._model

        embeddings.get_model = fake_get
        try:
            m1 = embeddings.get_model("test-model")
            m2 = embeddings.get_model("test-model")
            assert m1 is mock_instance
            assert m2 is mock_instance
        finally:
            embeddings.get_model = original_get
            embeddings._model = None
