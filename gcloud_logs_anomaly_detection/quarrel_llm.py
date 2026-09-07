"""Longbow-Quarrel LLM wrapper for LangChain."""

from __future__ import annotations

from typing import Any

from gcloud_logs_anomaly_detection.config import QuarrelConfig

try:
    from langchain_core.language_models.llms import LLM

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


if LANGCHAIN_AVAILABLE:
    class QuarrelLLM(LLM):  # type: ignore[no-redef]
        """LangChain LLM wrapper for Longbow-Quarrel OpenAI-compatible API."""

        base_url: str = "http://localhost:8080"
        api_key: str = ""
        model: str = "default"
        temperature: float = 0.0
        max_tokens: int = 4096

        def _call(
            self,
            prompt: str,
            stop: list[str] | None = None,
            **kwargs: Any,
        ) -> str:
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package is required for Quarrel backend")
            client = OpenAI(
                base_url=f"{self.base_url}/v1",
                api_key=self.api_key or "none",
            )
            params: dict[str, Any] = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            if stop:
                params["stop"] = stop
            response = client.chat.completions.create(**params)
            content = response.choices[0].message.content
            return content if content is not None else ""

        @property
        def _llm_type(self) -> str:
            return "quarrel"


def create_quarrel_llm(config: QuarrelConfig | None = None) -> Any:
    """Create a Quarrel LLM instance from config."""
    if not LANGCHAIN_AVAILABLE:
        raise ImportError("langchain-core is required for Quarrel backend")
    if config is None:
        config = QuarrelConfig()
    return QuarrelLLM(
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
