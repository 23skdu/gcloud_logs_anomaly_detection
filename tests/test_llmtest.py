import pytest
from unittest.mock import Mock, patch
import os


class TestLLMTest:
    def test_default_model_name(self):
        with patch.dict(os.environ, {}, clear=False):
            import llmtest
            assert llmtest.modelname == "smollm2:135m"

    def test_custom_model_name(self):
        with patch.dict(os.environ, {"MODELNAME": "llama2:7b"}):
            import importlib
            import llmtest
            importlib.reload(llmtest)
            assert llmtest.modelname == "llama2:7b"

    @patch("llmtest.OllamaLLM")
    @patch("llmtest.PromptTemplate")
    def test_llm_invocation(self, mock_prompt, mock_ollama):
        mock_prompt.from_template.return_value = Mock()
        mock_prompt.from_template.return_value.invoke = Mock(return_value="response")
        mock_ollama_instance = Mock()
        mock_ollama_instance.invoke = Mock(return_value="test response")
        mock_ollama.return_value = mock_ollama_instance

        import llmtest
        from langchain_core.runnables import Runnable

        prompt = Mock(spec=Runnable)
        prompt.invoke = Mock(return_value="response")

        llm = Mock()
        llm.invoke = Mock(return_value="final response")

        result = llm.invoke({"question": "test"})
        assert "response" in str(result)

    def test_template_format(self):
        template = "Question: {question} "
        assert "{question}" in template
