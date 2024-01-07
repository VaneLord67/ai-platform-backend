from typing import Union

import redis

from common.config import config

if __name__ == '__main__':
    client: Union[redis.StrictRedis, None] = redis.StrictRedis.from_url(config.get("redis_url"))
    result = client.type(name='206b3641-65eb-4fed-8613-aee1faaf80aa1')
    print(type(result))
    print(result)

