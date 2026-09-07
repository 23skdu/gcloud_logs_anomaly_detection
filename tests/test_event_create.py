import os
from unittest.mock import patch

from gcloud_logs_anomaly_detection.config import EventCreateConfig
from gcloud_logs_anomaly_detection.exceptions import GCPAPIError


class TestEventCreate:
    def test_event_create_config_defaults(self):
        config = EventCreateConfig()
        assert config.num_events == 1000
        assert config.log_name == "loremipsumevents"

    def test_event_create_config_custom(self):
        config = EventCreateConfig(num_events=500, log_name="custom-logs")
        assert config.num_events == 500
        assert config.log_name == "custom-logs"

    def test_lorem_import(self):
        from lorem_text import lorem

        sentence = lorem.sentence()
        assert isinstance(sentence, str)
        assert len(sentence) > 0

    def test_get_num_events_default(self):
        with patch.dict(os.environ, {}, clear=False):
            from gcloud_event_create import get_num_events

            assert get_num_events() == 1000

    def test_get_num_events_custom(self):
        with patch.dict(os.environ, {"NUMEVENTS": "500"}):
            from gcloud_event_create import get_num_events

            assert get_num_events() == 500

    def test_get_log_name_default(self):
        from gcloud_event_create import get_log_name

        assert get_log_name() == "loremipsumevents"

    def test_gcp_api_error(self):
        exc = GCPAPIError("test error")
        assert str(exc) == "test error"
