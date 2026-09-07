import os
from unittest.mock import Mock, patch

from gcloud_logs_anomaly_detection.config import LLMTestConfig


class TestLLMTest:
    def test_llm_test_config_defaults(self):
        config = LLMTestConfig()
        assert config.model_name == "smollm2:135m"

    def test_llm_test_config_custom(self):
        config = LLMTestConfig(model_name="llama2:7b")
        assert config.model_name == "llama2:7b"

    def test_default_model_name(self):
        from llmtest import get_model_name

        with patch.dict(os.environ, {}, clear=False):
            assert get_model_name() == "smollm2:135m"

    def test_custom_model_name(self):
        from llmtest import get_model_name

        with patch.dict(os.environ, {"MODELNAME": "llama2:7b"}):
            assert get_model_name() == "llama2:7b"

    def test_create_prompt_template(self):
        from llmtest import create_prompt_template

        prompt = create_prompt_template()
        assert "{question}" in prompt.template

    def test_llm_invocation(self):

        mock_llm = Mock()
        mock_llm.invoke.return_value = "test response"
        mock_prompt = Mock()
        mock_prompt.__or__ = Mock(return_value=Mock(invoke=Mock(return_value="test response")))

        result = mock_llm.invoke({"question": "test"})
        assert "response" in str(result)
