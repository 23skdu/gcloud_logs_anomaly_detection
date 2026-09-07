# Next Steps - Improvement Plan

> Generated from deep code analysis on 2026-09-06

## 10-Part Improvement Plan

### 1. Dependency Version Synchronization

**Status:** Done (Dockerfile updated, requirements.txt current)

The Dockerfile was pinned to severely outdated versions (e.g., `pandas==2.3.3` vs `requirements.txt` 3.0.5, `langchain==0.3.17` vs 1.3.16). All Dockerfile pins now match requirements.txt. Dependabot PRs (#73-#77) for remaining minor bumps should be merged.

### 2. Package Structure Refactor

**Status:** Pending

- Add `__init__.py` to project root for proper package import
- Create `__main__.py` to support `python -m gcloud_logs_anomaly_detection`
- Currently the Dockerfile CMD was referencing a non-existent module; fix applied as interim
- Refactor scripts into a proper package layout under `src/gcloud_logs_anomaly_detection/`

### 3. Test Suite Corrections

**Status:** Pending

Tests in `tests/test_event_create.py` and `tests/test_llmtest.py` reference module-level attributes (`numevents`, `logname`, `modelname`) that no longer exist after the pydantic-settings refactor. These tests need to be rewritten to test the actual function-based API and pydantic config classes. Run `pytest` after fixes to confirm all pass.

### 4. Type Annotation Hardening

**Status:** Pending

- Enable `disallow_untyped_defs = true` in mypy config
- Add return type annotations to all public functions
- Replace `Any` type hints with concrete types where possible (e.g., `llmtest.py` return types)
- Add `py.typed` marker for downstream consumers

### 5. Error Handling & Resilience

**Status:** Pending

- `gcloud_logs_detect.py:load_logs()` has no error handling for GCP API failures
- `gcloud_logs_llmsummary.py:get_log_entries()` should implement retry with exponential backoff for transient `ClientError`s
- Add structured exception hierarchy for GCP-specific errors vs LLM errors
- Validate `GCP_PROJECT` is set before attempting any GCP operations

### 6. CLI Framework Integration

**Status:** Pending

Replace basic `argparse`/env-var-only interfaces with a unified CLI using `click` or `typer`:
- `gcloud-anomaly detect --log-name X --contamination auto`
- `gcloud-anomaly summarize --project-id X --hours-ago 1`
- `gcloud-anomaly generate --num-events 1000`
- `gcloud-anomaly test --model smollm2:135m`
- Preserve backward compatibility via env vars as fallback

### 7. Observability & Metrics

**Status:** Pending

- The `@timeit` decorator in `gcloud_logs_llmsummary.py` is a good start; extend it to all scripts
- Add structured JSON logging (replace `print()` with `logging` module)
- Emit metrics for: log entry count, anomaly count, LLM latency, chunk count
- Add optional OpenTelemetry tracing for GCP API and LLM calls
- Create a `/health` endpoint if containerized as a service

### 8. CI/CD Pipeline Enhancements

**Status:** Pending

- Auto-merge dependabot PRs that pass all checks (currently 5 PRs waiting)
- Add security scanning workflow (e.g., `safety`, `trivy`, or `scorecard`)
- Add integration test workflow that runs against a real GCP project (with secrets)
- Cache pip dependencies in CI for faster builds
- Add Docker image vulnerability scanning to the publish workflow

### 9. Docker Image Optimization

**Status:** Pending

- Switch to multi-stage build: builder stage for pip install, slim runtime stage
- Use `COPY --from=builder` to reduce final image size
- Pin `python:3.14-slim` (currently used, good) but add `.dockerignore` to exclude `.git/`, `tests/`, `docs/`
- Run as non-root user for security (`USER --uid=1000 appuser`)
- Add `HEALTHCHECK` instruction

### 10. Configuration Validation & Profiles

**Status:** Pending

- `config.py` has `LLMConfig` with empty `env_prefix` — consider prefixing with `LLM_` for clarity
- Add validation rules: `project_id` should be required (not default empty string)
- Support environment profiles (dev/staging/prod) via `ENVIRONMENT` variable
- Add config schema documentation auto-generation from pydantic models
- Add runtime validation that all required GCP env vars are set before operations begin

---

## Resolved Items (Removed)

*No prior nextsteps.md existed — this is the initial plan created from codebase analysis.*
