# Local LLM Test Script

This script (`llmtest.py`) is a utility to test a local Ollama LLM instance.

## Features

- Connects to a local Ollama instance.
- Sends a user-provided question to the model.
- Prints the response.
- Performance timing via `@timeit` decorator.

## Usage

```bash
python llmtest.py "Why is the sky blue?"
```

Or via the unified CLI:

```bash
gcloud-anomaly ask "Why is the sky blue?"
```

### Options

- `--model MODELNAME` — Override the Ollama model (env: `MODELNAME`)

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `MODELNAME` | Name of the Ollama model to use | `smollm2:135m` |
