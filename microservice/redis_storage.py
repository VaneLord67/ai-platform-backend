from typing import Union

from nameko.extensions import DependencyProvider

import redis

from common.config import config


class RedisStorageWrapper:

    def __init__(self, client):
        self.client = client


class RedisStorage(DependencyProvider):

    def __init__(self):
        self.client: Union[redis.StrictRedis, None] = None

    def setup(self):
        self.client: Union[redis.StrictRedis, None] = redis.StrictRedis.from_url(config.get("redis_url"))

    def get_dependency(self, worker_ctx):
        return RedisStorageWrapper(self.client)
