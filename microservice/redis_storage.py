from nameko.extensions import DependencyProvider

import redis

from common.config import config


class RedisStorageWrapper:

    def __init__(self, client):
        self.client = client


class RedisStorage(DependencyProvider):

    def __init__(self):
        self.client: redis.StrictRedis = None

    def setup(self):
        self.client: redis.StrictRedis = redis.StrictRedis.from_url(config.get("redis_url"))

    def get_dependency(self, worker_ctx):
        return RedisStorageWrapper(self.client)
