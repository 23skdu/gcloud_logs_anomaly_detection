#!/usr/bin/env python3
import os,logging
import google.cloud.logging
from lorem_text import lorem
numevents = os.getenv('NUMEVENTS', 1000)
client = google.cloud.logging.Client()
client.setup_logging()
for i in range(numevents):
    message = lorem.sentence()
    logging.info(message)
client.flush_handlers()
