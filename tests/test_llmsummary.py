import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
import asyncio


class TestLLMSummary:
    def test_timeit_decorator(self):
        from gcloud_logs_llmsummary import timeit

        @timeit
        def slow_function():
            import time
            time.sleep(0.01)
            return "done"

        result = slow_function()
        assert result == "done"

    def test_get_log_entries_returns_list(self):
        from gcloud_logs_llmsummary import get_log_entries

        mock_client = Mock()
        mock_entry = Mock()
        mock_entry.timestamp = datetime.now(timezone.utc)
        mock_entry.severity = "INFO"
        mock_entry.payload = "Test message"
        mock_entry.resource = "test-resource"
        mock_entry.labels = {"key": "value"}
        mock_client.list_entries.return_value = iter([mock_entry])

        with patch("gcloud_logs_llmsummary.gcp_logging.Client", return_value=mock_client):
            logs = get_log_entries("test-project", "severity >= INFO", hours_ago=1)
            assert isinstance(logs, list)
            assert len(logs) == 1
            assert logs[0]["severity"] == "INFO"

    def test_summarize_logs_empty(self):
        from gcloud_logs_llmsummary import summarize_logs
        mock_llm = Mock()
        result = summarize_logs([], mock_llm)
        assert result == "No log entries to summarize."

    def test_summarize_logs_formats_correctly(self):
        from gcloud_logs_llmsummary import summarize_logs
        mock_llm = Mock()
        mock_llm.invoke.return_value = "Summary"

        logs = [
            {
                "timestamp": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                "severity": "ERROR",
                "message": "Test error",
                "resource": "test-resource",
                "labels": {"env": "prod"},
            }
        ]

        with patch("gcloud_logs_llmsummary.RecursiveCharacterTextSplitter"):
            result = summarize_logs(logs, mock_llm)
            assert isinstance(result, str)

    def test_async_scheduled_task(self):
        from gcloud_logs_llmsummary import scheduled_task, run_log_summarization
        import gcloud_logs_llmsummary

        with patch.object(gcloud_logs_llmsummary, "run_log_summarization") as mock_run:
            mock_run.return_value = asyncio.Future()
            mock_run.return_value.set_result(None)

            async def quick_test():
                task = asyncio.create_task(scheduled_task("test", "filter", "model", 1))
                await asyncio.sleep(0.1)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            asyncio.run(quick_test())
            mock_run.assert_called_once()

    def test_project_id_required(self):
        import os
        from gcloud_logs_llmsummary import PROJECT_ID

        if not PROJECT_ID:
            with patch.dict(os.environ, {"GCP_PROJECT": ""}):
                with pytest.raises(SystemExit):
                    pass
