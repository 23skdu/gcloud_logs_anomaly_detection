"""Configuration management for gcloud-logs-anomaly-detection."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DetectConfig(BaseSettings):
    """Configuration for anomaly detection."""

    log_name: str = Field(default="loremipsumevents", description="GCP log name to monitor")
    page_size: int = Field(default=10000, description="Number of log entries to fetch")
    contamination: str = Field(
        default="auto", description="Contamination parameter for IsolationForest"
    )
    n_estimators: int = Field(default=100, description="Number of trees in IsolationForest")
    test_size: float = Field(default=0.2, description="Test/train split ratio")
    random_state: int = Field(default=42, description="Random seed for reproducibility")

    model_config = SettingsConfigDict(env_prefix="LOG_")


class LLMConfig(BaseSettings):
    """Configuration for LLM summarization."""

    project_id: str = Field(
        default="", description="GCP Project ID (required)", alias="GCP_PROJECT"
    )
    log_filter: str = Field(default="severity >= INFO", description="Log filter query")
    model_name: str = Field(
        default="gemini-2.0-flash-lite", description="LLM model to use"
    )
    hours_ago: int = Field(default=1, description="Hours of logs to fetch")
    temperature: float = Field(default=0.0, description="LLM temperature")
    chunk_size: int = Field(default=2000, description="Text chunk size for LLM")
    chunk_overlap: int = Field(default=100, description="Chunk overlap for LLM")
    interval_hours: int = Field(default=1, description="Hours between scheduled runs")

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    @field_validator("project_id", mode="after")
    @classmethod
    def _validate_project_id(cls, v: str) -> str:
        if not v:
            import os

            v = os.environ.get("GCP_PROJECT", "")
        return v


class EventCreateConfig(BaseSettings):
    """Configuration for test event generation."""

    num_events: int = Field(default=1000, description="Number of events to generate")
    log_name: str = Field(default="loremipsumevents", description="GCP log name")

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")


class LLMTestConfig(BaseSettings):
    """Configuration for local LLM testing."""

    model_name: str = Field(
        default="smollm2:135m",
        description="Ollama model name",
    )

    model_config = SettingsConfigDict(env_prefix="MODEL_", extra="ignore")
