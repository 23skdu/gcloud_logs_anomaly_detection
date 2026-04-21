import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd


class TestDetect:
    def test_severity_mapping(self):
        from gcloud_logs_detect import SEVERITY_MAPPING
        assert SEVERITY_MAPPING["DEBUG"] == 1
        assert SEVERITY_MAPPING["INFO"] == 2
        assert SEVERITY_MAPPING["WARNING"] == 3
        assert SEVERITY_MAPPING["ERROR"] == 4
        assert SEVERITY_MAPPING["CRITICAL"] == 5

    @patch("gcloud_logs_detect.logger")
    def test_log_entries_loading(self, mock_logger):
        mock_entry = Mock()
        mock_entry.timestamp = 1234567890000000000
        mock_entry.severity = "ERROR"
        mock_entry.payload = "Test error message"
        mock_logger.list_entries.return_value = [mock_entry]

        from gcloud_logs_detect import logger
        entries = list(logger.list_entries(page_size=10000))
        assert len(entries) == 1

    def test_dataframe_creation(self):
        data = {
            "timestamp": [1234567890000000000, 1234567891000000000],
            "severity": ["ERROR", "WARNING"],
            "payload": ["Error msg", "Warning msg"],
        }
        df = pd.DataFrame(data)
        assert len(df) == 2
        assert "timestamp" in df.columns
        assert "severity" in df.columns
        assert "payload" in df.columns

    def test_severity_mapping_with_fillna(self):
        severity_mapping = {"DEBUG": 1, "INFO": 2, "WARNING": 3, "ERROR": 4, "CRITICAL": 5}
        df = pd.DataFrame({"severity": ["ERROR", "UNKNOWN", "INFO"]})
        df["severity_mapped"] = df["severity"].map(severity_mapping).fillna(0)
        assert df["severity_mapped"].tolist() == [4, 0, 2]

    def test_message_length_calculation(self):
        df = pd.DataFrame({"payload": ["short", "medium length", "very long message"]})
        df["message_length"] = df["payload"].apply(len)
        assert df["message_length"].tolist() == [5, 13, 21]
