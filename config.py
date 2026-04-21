"""Configuration management for gcloud-logs-anomaly-detection."""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DetectConfig(BaseSettings):
    """Configuration for gcloud_logs_detect.py"""

    log_name: str = Field(default="loremipsumevents", description="GCP log name to monitor")
    page_size: int = Field(default=10000, description="Number of log entries to fetch")
    contamination: str = Field(default="auto", description="Contamination parameter for IsolationForest")
    n_estimators: int = Field(default=100, description="Number of trees in IsolationForest")
    test_size: float = Field(default=0.2, description="Test/train split ratio")
    random_state: int = Field(default=42, description="Random seed for reproducibility")

    model_config = SettingsConfigDict(env_prefix="LOG_")


class LLMConfig(BaseSettings):
    """Configuration for gcloud_logs_llmsummary.py"""

    project_id: str = Field(default="", description="GCP Project ID (required)")
    log_filter: str = Field(default="severity >= INFO", description="Log filter query")
    model_name: str = Field(default="gemini-2.0-flash-lite", description="LLM model to use")
    hours_ago: int = Field(default=1, description="Hours of logs to fetch")
    temperature: float = Field(default=0.0, description="LLM temperature")
    chunk_size: int = Field(default=2000, description="Text chunk size for LLM")
    chunk_overlap: int = Field(default=100, description="Chunk overlap for LLM")

    model_config = SettingsConfigDict(env_prefix="")


class EventCreateConfig(BaseSettings):
    """Configuration for gcloud_event_create.py"""

    num_events: int = Field(default=1000, description="Number of events to generate")
    log_name: str = Field(default="loremipsumevents", description="GCP log name")

    model_config = SettingsConfigDict(env_prefix="")


class LLMTestConfig(BaseSettings):
    """Configuration for llmtest.py"""

    model_name: str = Field(default="smollm2:135m", description="Ollama model name")

    model_config = SettingsConfigDict(env_prefix="")
