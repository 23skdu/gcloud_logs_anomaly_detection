from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from gcloud_logs_anomaly_detection.config import LLMConfig
from gcloud_logs_anomaly_detection.exceptions import GCPAPIError, GCPConfigError


class TestLLMSummary:
    def test_timeit_decorator(self) -> None:
        from gcloud_logs_anomaly_detection.observability import timeit

        @timeit
        def slow_function() -> str:
            import time

            time.sleep(0.01)
            return "done"

        result = slow_function()
        assert result == "done"

    def test_llm_config_defaults(self) -> None:
        config = LLMConfig(project_id="test-project")
        assert config.model_name == "gemini-2.0-flash-lite"
        assert config.hours_ago == 1
        assert config.temperature == 0.0
        assert config.chunk_size == 2000
        assert config.chunk_overlap == 100
        assert config.interval_hours == 1

    def test_get_log_entries_returns_list(self) -> None:
        from scripts.gcloud_logs_llmsummary import get_log_entries

        mock_client = Mock()
        mock_entry = Mock()
        mock_entry.timestamp = datetime.now(UTC)
        mock_entry.severity = "INFO"
        mock_entry.payload = "Test message"
        mock_entry.resource = "test-resource"
        mock_entry.labels = {"key": "value"}
        mock_client.list_entries.return_value = iter([mock_entry])

        with patch("scripts.gcloud_logs_llmsummary.gcp_logging.Client", return_value=mock_client):
            logs = get_log_entries("test-project", "severity >= INFO", hours_ago=1)
            assert isinstance(logs, list)
            assert len(logs) == 1
            assert logs[0]["severity"] == "INFO"

    def test_get_log_entries_empty_project(self) -> None:
        from scripts.gcloud_logs_llmsummary import get_log_entries

        with pytest.raises(GCPConfigError):
            get_log_entries("", "severity >= INFO", hours_ago=1)

    def test_summarize_logs_empty(self) -> None:
        from scripts.gcloud_logs_llmsummary import summarize_logs

        mock_llm = Mock()
        result = summarize_logs([], mock_llm)
        assert result == "No log entries to summarize."

    def test_summarize_logs_formats_correctly(self) -> None:
        from scripts.gcloud_logs_llmsummary import summarize_logs

        sample_entries = [
            {
                "timestamp": datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
                "severity": "ERROR",
                "message": "Test error",
                "resource": "test-resource",
                "labels": {"env": "prod"},
            }
        ]

        with patch("scripts.gcloud_logs_llmsummary.RecursiveCharacterTextSplitter") as mock_splitter:
            mock_splitter.return_value.split_text.return_value = ["chunk1"]
            mock_llm = Mock()
            with patch("scripts.gcloud_logs_llmsummary.PromptTemplate") as mock_prompt_cls:
                mock_prompt = Mock()
                chain_mock = Mock()
                chain_mock.invoke.return_value = "Test summary output"
                chain_mock.__or__ = Mock(return_value=chain_mock)
                mock_prompt.__ror__ = Mock(return_value=chain_mock)
                mock_prompt_cls.from_template.return_value = mock_prompt

                with (
                    patch("scripts.gcloud_logs_llmsummary.StrOutputParser"),
                    patch("scripts.gcloud_logs_llmsummary.RunnablePassthrough"),
                    patch("builtins.print"),
                ):
                    result = summarize_logs(sample_entries, mock_llm)
                    assert "Test summary output" in result

    def test_exceptions_hierarchy(self) -> None:
        from gcloud_logs_anomaly_detection.exceptions import (
            GCloudAnomalyError,
            GCPConfigError,
            LLMSummarizationError,
        )

        assert issubclass(GCPConfigError, GCloudAnomalyError)
        assert issubclass(GCPAPIError, GCloudAnomalyError)
        assert issubclass(LLMSummarizationError, GCloudAnomalyError)
