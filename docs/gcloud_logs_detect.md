# Google Cloud Logs Anomaly Detection

This script (gcloud_logs_detect.py) fetches logs from Google Cloud, analyzes
them for anomalies using Machine Learning, and visualizes the results.

## Features

- Fetches logs using the Google Cloud Logging API.
- Preprocesses data: maps severity levels to integers, calculates message length.
- Uses **Isolation Forest** (scikit-learn) to detect anomalies based on timestamp, severity, and message length.
- Generates a scatter plot (anomaly_detection.png) visualizing anomalies.

## Configuration

- LOG_NAME: Name of the log to analyze (default: 'loremipsumevents').
