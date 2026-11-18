# gcloud-logs-anomaly-detection developer tasks

SHELL := /bin/bash
.DEFAULT_GOAL := help

PROJECT := gcloud-logs-anomaly-detection
GHCR_IMAGE := ghcr.io/23skdu/gcloud_logs_anomaly_detection
VENV := .venv
PYTHON ?= $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)

DOCKER_IMAGES := \
	$(PROJECT):latest \
	$(GHCR_IMAGE):latest \
	$(GHCR_IMAGE):1.0.0

.PHONY: help install lint format test security pre-commit \
	clean clean-all clean-python clean-test clean-build clean-caches \
	clean-venv clean-docker clean-docker-cache

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the project and development dependencies into .venv
	@if [ ! -x "$(VENV)/bin/python" ]; then python3 -m venv $(VENV); fi
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/python -m pip install -e ".[dev]"

lint: ## Run Ruff and mypy
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m mypy .

format: ## Format and auto-fix Python code
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

test: ## Run the test suite
	$(PYTHON) -m pytest

security: ## Run dependency and static security checks
	$(PYTHON) -m pip_audit -r requirements.txt --strict
	$(PYTHON) -m bandit -q -ll -r gcloud_logs_anomaly_detection scripts

pre-commit: ## Run all pre-commit hooks
	$(PYTHON) -m pre_commit run --all-files

clean: clean-python clean-venv clean-docker ## Remove artifacts, caches, venv and project Docker images

clean-all: clean clean-docker-cache ## clean plus the global Docker builder cache

clean-python: clean-test clean-build clean-caches ## Remove all Python artifacts and tool caches

clean-test: ## Remove test and coverage artifacts
	rm -rf .pytest_cache .tox .nox htmlcov .coverage .coverage.* coverage.xml
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.py[co]' -o -name '*.pyo' -o -name '*.pyd' \) -delete

clean-build: ## Remove Python build artifacts
	rm -rf build dist .eggs *.egg-info pip-wheel-metadata site

clean-caches: ## Remove local tool caches
	rm -rf .mypy_cache .ruff_cache .cache

clean-venv: ## Remove local virtual environments
	rm -rf $(VENV)

clean-docker: ## Remove locally tagged project Docker images
	@command -v docker >/dev/null 2>&1 || { echo "docker not found; skipping"; exit 0; }
	@for image in $(DOCKER_IMAGES); do \
		docker image rm -f "$$image" >/dev/null 2>&1 || true; \
	done
	@echo "Removed local project Docker images"

clean-docker-cache: ## Prune the global Docker builder cache
	@command -v docker >/dev/null 2>&1 || { echo "docker not found; skipping"; exit 0; }
	docker builder prune -f
