import pandas as pd

from gcloud_logs_anomaly_detection.config import DetectConfig


class TestDetect:
    def test_severity_mapping(self):
        from gcloud_logs_detect import SEVERITY_MAPPING

        assert SEVERITY_MAPPING["DEBUG"] == 1
        assert SEVERITY_MAPPING["INFO"] == 2
        assert SEVERITY_MAPPING["WARNING"] == 3
        assert SEVERITY_MAPPING["ERROR"] == 4
        assert SEVERITY_MAPPING["CRITICAL"] == 5

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
        assert df["message_length"].tolist() == [5, 13, 17]

    def test_detect_config_defaults(self):
        config = DetectConfig()
        assert config.log_name == "loremipsumevents"
        assert config.page_size == 10000
        assert config.contamination == "auto"
        assert config.n_estimators == 100
        assert config.test_size == 0.2
        assert config.random_state == 42

    def test_preprocess_logs(self):
        from gcloud_logs_detect import preprocess_logs

        df = pd.DataFrame(
            {
                "timestamp": [1234567890000000000, 1234567891000000000],
                "severity": ["ERROR", "WARNING"],
                "payload": ["Error msg", "Warning msg"],
            }
        )
        result = preprocess_logs(df)
        assert result["severity"].tolist() == [4, 3]
        assert result["message_length"].tolist() == [9, 11]
