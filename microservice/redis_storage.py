from typing import Union

from nameko.extensions import DependencyProvider

import redis

from common.config import config
from common.util import create_redis_client


class RedisStorageWrapper:

    def __init__(self, client):
        self.client = client


class RedisStorage(DependencyProvider):

    def __init__(self):
        self.client: Union[redis.StrictRedis, None] = None

    def setup(self):
        self.client: create_redis_client()

    def get_dependency(self, worker_ctx):
        return RedisStorageWrapper(self.client)
