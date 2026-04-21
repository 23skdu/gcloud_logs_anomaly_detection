#!/usr/bin/env python3
"""Anomaly detection for Google Cloud Logging using Isolation Forest."""

import os
import datetime
from typing import Any

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from google.cloud import logging

SEVERITY_MAPPING: dict[str, int] = {
    "DEBUG": 1,
    "INFO": 2,
    "WARNING": 3,
    "ERROR": 4,
    "CRITICAL": 5,
}


def get_log_name() -> str:
    """Get the log name from environment or use default."""
    return os.getenv("LOG_NAME", "loremipsumevents")


def load_logs(log_name: str, page_size: int = 10000) -> pd.DataFrame:
    """Load logs from Google Cloud Logging."""
    client = logging.Client()
    logger = client.logger(log_name)
    entries = logger.list_entries(page_size=page_size)
    return pd.DataFrame(entries)


def preprocess_logs(df: pd.DataFrame) -> pd.DataFrame:
    """Preprocess log DataFrame for anomaly detection."""
    df = df.copy()
    df["timestamp"] = df["timestamp"].astype("int64")
    df["severity"] = df["severity"].map(SEVERITY_MAPPING).fillna(0)
    df["message_length"] = df["payload"].apply(len)
    return df


def detect_anomalies(
    df: pd.DataFrame,
    test_size: float = 0.2,
    contamination: str = "auto",
    n_estimators: int = 100,
    random_state: int = 42,
) -> pd.DataFrame:
    """Detect anomalies using Isolation Forest."""
    X = df[["timestamp", "severity", "message_length"]]
    X_train, X_test = train_test_split(X, test_size=test_size, random_state=random_state)
    scaler = StandardScaler()
    Z_train = scaler.fit_transform(X_train)
    Z_test = scaler.transform(X_test)
    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
    )
    model.fit(Z_train)
    y_pred = model.predict(Z_test)
    anomaly_indices = [i for i, pred in enumerate(y_pred) if pred == -1]
    df["anomaly"] = df.index.isin(anomaly_indices)
    return df


def visualize_anomalies(df: pd.DataFrame, output_path: str = "anomaly_detection.png") -> None:
    """Create visualization of detected anomalies."""
    sns.scatterplot(
        x=df.index,
        y=df["message_length"],
        hue="anomaly",
        data=df,
        palette={True: "red", False: "blue"},
    )
    plt.title("Anomaly Detection in Google Cloud Logs")
    plt.xlabel("Log Entry Index")
    plt.ylabel("Log Message Length")
    plt.savefig(output_path)
    plt.close()


def main() -> None:
    """Main entry point for anomaly detection."""
    log_name = get_log_name()
    df = load_logs(log_name)
    df = preprocess_logs(df)
    df = detect_anomalies(df)
    visualize_anomalies(df)
    print(f"Analysis complete. Found {df['anomaly'].sum()} anomalies out of {len(df)} entries.")


if __name__ == "__main__":
    main()
