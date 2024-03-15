import json
import logging
import socket
import time

import psutil
from GPUtil import GPUtil
from nameko.extensions import DependencyProvider

from common.util import create_redis_client


class LoadDependency(DependencyProvider):
    load_zset_key_name = "zset_load_hosts"
    report_interval = 5  # unit: seconds
    circular_queue_max_length = 30

    def __init__(self):
        self.redis_client = None

    def setup(self):
        self.redis_client = create_redis_client()
        self.report_live_to_redis()
        self.report_load_to_redis()

    def get_dependency(self, worker_ctx):
        return self

    def report_live_to_redis(self):
        # 向redis的一个zset中上报当前主机的主机名
        # zset的score存储过期时间戳，用于淘汰离线主机
        logging.info("report live to redis")
        redis_client = self.redis_client
        load = self.get_current_host_load()
        hostname = load['hostname']
        redis_client.zadd(self.load_zset_key_name, {hostname: time.time() + self.report_interval * 2})

    def report_load_to_redis(self):
        # 使用redis lua脚本，实现循环队列，用于存储近一段时间的负载数据
        redis_client = self.redis_client
        script_content = """
                -- KEYS[1] 是列表的键名
                -- ARGV[1] 是要入队的元素
                -- ARGV[2] 是队列的最大长度
                -- ARGV[3] 是队列的过期时间（秒）

                -- 获取当前队列长度
                local length = redis.call('LLEN', KEYS[1])

                -- 如果队列已满，则移除队列头部元素
                if length >= tonumber(ARGV[2]) then
                    redis.call('LPOP', KEYS[1])
                end

                -- 将新元素入队
                redis.call('RPUSH', KEYS[1], ARGV[1])

                -- 设置队列的过期时间
                redis.call('EXPIRE', KEYS[1], ARGV[3])

                return 1  -- 表示入队操作成功
                """
        load = self.get_current_host_load()
        hostname = load.pop('hostname')
        redis_client.eval(script_content, 1, f"load_circular_queue_{hostname}",
                          json.dumps(load), self.circular_queue_max_length, self.report_interval * 4)
        logging.info(f"report load to redis, load: {load}")

    @staticmethod
    def get_current_host_load():
        gpus = GPUtil.getGPUs()
        gpu_percent = [gpu.load for gpu in gpus]
        load = {
            'hostname': socket.gethostname(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "gpu_percent": gpu_percent,
            "time": time.time()
        }
        return load
