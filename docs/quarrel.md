# Quarrel Inference Guide

This document describes how to use [Longbow-Quarrel](https://github.com/23skdu/longbow-quarrel) as an inference backend.

## Overview

Quarrel is a high-performance Go LLM inference engine with an OpenAI-compatible API. Use it as a local alternative to Google Gemini or Ollama.

### Features

- **OpenAI-compatible API** (`/v1/chat/completions`)
- **Zero-copy quantized inference** (Q4_K, Q6_K, Q8_0, FP16, FP32)
- **GPU acceleration** (Apple Silicon Metal, NVIDIA CUDA)
- **CPU SIMD** (AVX-512, AVX2, ARM NEON)
- **Universal model resolver** (HuggingFace, Ollama, llama.cpp caches)

## Setup

### Prerequisites

1. A running Quarrel instance (see [Quarrel docs](https://github.com/23skdu/longbow-quarrel))
2. Python dependency: `pip install openai`

### Quick Start with Docker Compose

```bash
docker compose -f docker-compose.longbow.yml up quarrel
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `QUARREL_BASE_URL` | Quarrel API base URL | `http://localhost:8080` |
| `QUARREL_API_KEY` | API key (if configured) | (empty) |
| `QUARREL_MODEL` | Model name | `default` |
| `QUARREL_TEMPERATURE` | LLM temperature | `0.0` |
| `QUARREL_MAX_TOKENS` | Max generation tokens | `4096` |

## Usage

### CLI: Summarize with Quarrel

```bash
gcloud-anomaly summarize --project-id my-project --backend quarrel
```

### CLI: Select Backend

```bash
gcloud-anomaly summarize --backend gemini   # Google Gemini (default)
gcloud-anomaly summarize --backend quarrel  # Local Quarrel
gcloud-anomaly summarize --backend ollama   # Local Ollama
```

### Python API

```python
from gcloud_logs_anomaly_detection.quarrel_llm import create_quarrel_llm

llm = create_quarrel_llm()
response = llm.invoke("Summarize these logs:")
```

### LangChain Integration

```python
from gcloud_logs_anomaly_detection.quarrel_llm import QuarrelLLM

llm = QuarrelLLM(
    base_url="http://localhost:8080",
    api_key="your-key",
    model="Qwen3.5",
    temperature=0.0,
)

# Use with LangChain chains
chain = prompt | llm | output_parser
result = chain.invoke({"logs": log_text})
```

## Architecture

```
gcloud-anomaly summarize --backend quarrel
    │
    ▼
gcloud_logs_llmsummary.py
    │
    ▼
create_llm(backend="quarrel")
    │
    ▼
QuarrelLLM (LangChain wrapper)
    │
    ▼
POST http://localhost:8080/v1/chat/completions
    │
    ▼
Quarrel inference engine (Go)
```

## Supported Models

Quarrel supports any GGUF model. Examples:

- `Qwen3.5` (hybrid SSM + attention)
- `mistral:latest`
- `Llama-3.2-3B`
- `gemma4`
- `smollm2`

Models are auto-resolved from `~/.cache/llmfit/models/`, `~/.cache/llama.cpp/`, `~/.cache/huggingface/hub/`, and `~/.ollama/models/`.
