from datetime import timedelta
from typing import Union

import redis

from common.config import config
from common.util import create_redis_client

if __name__ == '__main__':
    stopSignalKey = "test_stop"
    client = create_redis_client()
    client.set(stopSignalKey, "1", ex=timedelta(hours=1))
