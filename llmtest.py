#!/usr/bin/env python3
"""Test script for local Ollama LLM integration."""

import argparse
import os
from typing import Any, Dict

from langchain.prompts import PromptTemplate

try:
    from langchain_ollama import OllamaLLM
except ImportError as e:
    raise ImportError("langchain-ollama is required. Install with: pip install langchain-ollama") from e


def get_model_name() -> str:
    """Get the model name from environment or use default."""
    return os.getenv("MODELNAME", "smollm2:135m")


def create_prompt_template() -> PromptTemplate:
    """Create and return the prompt template."""
    template = "Question: {question} "
    return PromptTemplate(template=template, input_variables=["question"])


def create_llm(model_name: str) -> OllamaLLM:
    """Create and return an Ollama LLM instance."""
    return OllamaLLM(model=model_name)


def invoke_llm(llm: OllamaLLM, prompt: PromptTemplate, question: str) -> str:
    """Invoke the LLM with the given question."""
    runnable = prompt | llm
    response = runnable.invoke({"question": question})
    return response


def main() -> None:
    """Main entry point for LLM testing."""
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
