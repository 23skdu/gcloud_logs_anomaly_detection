#!/usr/bin/env python3
import os,logging
from google.cloud.logging import Client
from google.cloud.logging.handlers import CloudLoggingHandler
from lorem_text import lorem

numevents = os.getenv('NUMEVENTS', 1000)
logname = os.getenv('LOG_NAME', 'loremipsumevents')

client = Client()
handler = CloudLoggingHandler(client, name=logname)
logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

for i in range(numevents):
    message = lorem.sentence()
    logger.warning(message)
client.flush_handlers()
