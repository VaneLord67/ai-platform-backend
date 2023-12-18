from datetime import timedelta
from typing import Union

import redis

from common.config import config

if __name__ == '__main__':
    stopSignalKey = "test_stop"
    client: Union[redis.StrictRedis, None] = redis.StrictRedis.from_url(config.get("redis_url"))
    client.set(stopSignalKey, "1", ex=timedelta(hours=1))
