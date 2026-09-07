"""Tests for Quarrel LLM wrapper."""

from unittest.mock import MagicMock, patch

from gcloud_logs_anomaly_detection.config import QuarrelConfig


class TestQuarrelConfig:
    def test_defaults(self):
        config = QuarrelConfig()
        assert config.base_url == "http://localhost:8080"
        assert config.api_key == ""
        assert config.model == "default"
        assert config.temperature == 0.0
        assert config.max_tokens == 4096


class TestQuarrelLLM:
    def test_quarrel_llm_type(self):
        from gcloud_logs_anomaly_detection.quarrel_llm import QuarrelLLM

        llm = QuarrelLLM()
        assert llm._llm_type == "quarrel"

    @patch("gcloud_logs_anomaly_detection.quarrel_llm.OpenAI")
    def test_call(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello!"))]
        mock_client.chat.completions.create.return_value = mock_response

        from gcloud_logs_anomaly_detection.quarrel_llm import QuarrelLLM

        llm = QuarrelLLM(base_url="http://test:8080", api_key="key123")
        result = llm._call("test prompt")
        assert result == "Hello!"
        mock_openai_cls.assert_called_once_with(
            base_url="http://test:8080/v1", api_key="key123"
        )

    @patch("gcloud_logs_anomaly_detection.quarrel_llm.OpenAI")
    def test_call_empty_content(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]
        mock_client.chat.completions.create.return_value = mock_response

        from gcloud_logs_anomaly_detection.quarrel_llm import QuarrelLLM

        llm = QuarrelLLM()
        result = llm._call("test")
        assert result == ""

    def test_create_quarrel_llm_default(self):
        from gcloud_logs_anomaly_detection.quarrel_llm import create_quarrel_llm

        llm = create_quarrel_llm()
        assert llm._llm_type == "quarrel"
        assert llm.base_url == "http://localhost:8080"

    def test_create_quarrel_llm_custom(self):
        from gcloud_logs_anomaly_detection.quarrel_llm import create_quarrel_llm

        config = QuarrelConfig(base_url="http://custom:9090", api_key="abc")
        llm = create_quarrel_llm(config)
        assert llm.base_url == "http://custom:9090"
        assert llm.api_key == "abc"
