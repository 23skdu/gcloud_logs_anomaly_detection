"""Custom exception hierarchy for gcloud-logs-anomaly-detection."""


class GCloudAnomalyError(Exception):
    """Base exception for the application."""


class GCPConfigError(GCloudAnomalyError):
    """Raised when GCP configuration is invalid or missing."""


class GCPAPIError(GCloudAnomalyError):
    """Raised when a GCP API call fails."""

    def __init__(self, message: str, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.__cause__ = cause


class LLMSummarizationError(GCloudAnomalyError):
    """Raised when LLM summarization fails."""


class AnomalyDetectionError(GCloudAnomalyError):
    """Raised when anomaly detection processing fails."""
