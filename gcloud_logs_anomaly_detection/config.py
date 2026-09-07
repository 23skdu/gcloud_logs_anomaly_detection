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
    backend: str = Field(default="gemini", description="LLM backend (gemini|quarrel|ollama)")

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


class LongbowConfig(BaseSettings):
    """Configuration for Longbow vector storage."""

    uri: str = Field(
        default="grpc://localhost:3000", description="Longbow data port URI"
    )
    meta_uri: str = Field(
        default="grpc://localhost:3001", description="Longbow meta port URI"
    )
    dataset: str = Field(
        default="gcloud_logs", description="Longbow dataset name"
    )
    dims: int = Field(default=384, description="Embedding dimensions")
    data_type: str = Field(
        default="float32", description="Vector data type (float32|turboquant|int8)"
    )
    turboquant_bits: int = Field(default=4, description="TurboQuant compression bits (2|4|8)")
    search_k: int = Field(default=10, description="Default k for search")
    search_alpha: float = Field(
        default=0.7, description="Alpha for hybrid search (1.0=dense, 0.0=sparse)"
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Sentence-transformers model for embeddings"
    )

    model_config = SettingsConfigDict(env_prefix="LONGBOW_", extra="ignore")


class QuarrelConfig(BaseSettings):
    """Configuration for Longbow-Quarrel inference."""

    base_url: str = Field(
        default="http://localhost:8080", description="Quarrel API base URL"
    )
    api_key: str = Field(default="", description="Quarrel API key")
    model: str = Field(default="default", description="Quarrel model name")
    temperature: float = Field(default=0.0, description="LLM temperature")
    max_tokens: int = Field(default=4096, description="Max tokens for generation")

    model_config = SettingsConfigDict(env_prefix="QUARREL_", extra="ignore")
