#!/usr/bin/env python3
import os,datetime,json
import pandas as pd
from google.cloud import logging
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

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
