#!/usr/bin/env python3
import os,datetime,json
import pandas as pd
from google.cloud import logging
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import seaborn as sns
import matplotlib.pyplot as plt

severity_mapping = { 'DEBUG': 1, 'INFO': 2, 'WARNING': 3, 'ERROR': 4, 'CRITICAL': 5 }
logname = os.getenv('LOG_NAME', 'loremipsumevents')
df = pd.DataFrame()

#now = datetime.datetime.now(datetime.UTC)
#one_hr_ago = now - datetime.timedelta(hours=1)
#timestamp_filter = f'timestamp>="{one_hr_ago.isoformat()}" timestamp<="{now.isoformat()}"'
#entries = logger.list_entries(filter_=timestamp_filter)

client = logging.Client()
logger = client.logger(logname)

entries = logger.list_entries()
df = pd.DataFrame(entries)
df['timestamp'] = df['timestamp'].astype('int64')
df['severity'] = df['severity'].map(severity_mapping).fillna(0)

X = df[['timestamp','severity']]
scaler = StandardScaler()
Z = scaler.fit_transform(X)
Z_train, Z_test = train_test_split(X, test_size=0.2, random_state=42)
model = IsolationForest(n_estimators=100, contamination='auto', random_state=42)
model.fit(Z_train)
y_pred = model.predict(Z_test)

anomaly_indices = [i for i, pred in enumerate(y_pred) if pred == -1]
print("Anomaly Indices:", anomaly_indices)
