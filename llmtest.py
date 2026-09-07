#!/usr/bin/env python3
"""Test script for local Ollama LLM integration."""

from __future__ import annotations

import argparse
import os

try:
    from langchain_core.prompts import PromptTemplate
except ModuleNotFoundError:
    from langchain.prompts import PromptTemplate

from gcloud_logs_anomaly_detection.observability import setup_logging, timeit

try:
    from langchain_ollama import OllamaLLM
except ImportError as exc:
    raise ImportError(
        "langchain-ollama is required. Install with: pip install langchain-ollama"
    ) from exc


def get_model_name() -> str:
    """Get the model name from environment or use default."""
    import sys

    # Check CLI args first, then env, then default
    if len(sys.argv) > 2 and sys.argv[1] == "--model":
        return sys.argv[2]
    return os.getenv("MODELNAME", "smollm2:135m")


def create_prompt_template() -> PromptTemplate:
    """Create and return the prompt template."""
    template = "Question: {question} "
    return PromptTemplate(template=template, input_variables=["question"])


def create_llm(model_name: str) -> OllamaLLM:
    """Create and return an Ollama LLM instance."""
    return OllamaLLM(model=model_name)


@timeit
def invoke_llm(llm: OllamaLLM, prompt: PromptTemplate, question: str) -> str:
    """Invoke the LLM with the given question."""
    runnable = prompt | llm
    response: str = runnable.invoke({"question": question})
    return response


def main() -> None:
    """Main entry point for LLM testing."""
    setup_logging()
    parser = argparse.ArgumentParser(description="Ask a question to a local Ollama LLM.")
    parser.add_argument("question", help="The question to ask the LLM")
    args = parser.parse_args()

    model_name = get_model_name()
    prompt = create_prompt_template()
    llm = create_llm(model_name)

    response = invoke_llm(llm, prompt, args.question)
    print(response)


if __name__ == "__main__":
    main()
