import json
import os
import platform
import subprocess
import sys
import time
import uuid

from nameko.timer import timer

from common.log import LOGGER
from microservice.load_dependency import LoadDependency

sys.path.append("/usr/lib/x86_64-linux-gnu")

from nameko.events import EventDispatcher
from nameko.rpc import rpc

from microservice.redis_storage import RedisStorage
from model.service_info import ServiceInfo


class ManageService:
    name = "manage_service"

    dispatch = EventDispatcher()
    redis_storage = RedisStorage()
    load_dependency = LoadDependency()

    @timer(interval=load_dependency.report_interval)
    def report_live_to_redis(self):
        self.load_dependency.report_live_to_redis()

    @timer(interval=load_dependency.report_interval)
    def report_load_to_redis(self):
        self.load_dependency.report_load_to_redis()

    @rpc
    def get_current_load(self):
        load = self.load_dependency.get_current_host_load()
        return load

    @rpc
    def get_load(self):
        # 使用redis lua脚本，获取各个主机近一段时间的负载数据
        timestamp = int(time.time())
        lua_script = """
            -- KEYS[1] 是zset的键名
            -- ARGV[1] 是秒级Unix时间戳
           
            local now_timestamp = ARGV[1]
            redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now_timestamp)
            
            local members = redis.call('ZRANGE', KEYS[1], 0, -1)  -- 获取有序集合中的所有成员
            local result = {}  -- 存储最终结果的表
            for i, member in ipairs(members) do
                local list_key_name = 'load_circular_queue_' .. member  -- 加上前缀字符串
                local list_content = redis.call('LRANGE', list_key_name, 0, -1)  -- 获取列表中的内容
                table.insert(result, {member, list_content})
            end
            return result
        """
        redis_client = self.redis_storage.client
        host_load_data = redis_client.eval(lua_script, 1, self.load_dependency.load_zset_key_name, timestamp)
        ret = {}
        for host_load_datum in host_load_data:
            hostname = host_load_datum[0].decode('utf-8')
            ret[hostname] = []
            for load_datum in host_load_datum[1]:
                one_load = json.loads(load_datum.decode('utf-8'))
                # 将秒级时间戳的小数点部分截取掉
                one_load["time"] = int(one_load["time"])
                ret[hostname].append(one_load)
        return ret

    @rpc
    def change_state_to_ready(self, service_name, service_unique_id):
        self.dispatch(f"{service_name}state_change", service_unique_id)

    @rpc
    def get_services(self, service_name):
        services = []
        service_list_key = f"{service_name}_info"
        self.redis_storage.client.delete(service_list_key)
        self.dispatch(f"{service_name}state_report", service_list_key)
        time.sleep(0.5)
        list_elements = self.redis_storage.client.lrange(service_list_key, 0, -1)
        for service_info_str in list_elements:
            serviceInfo = ServiceInfo().from_json(service_info_str)
            services.append(serviceInfo)
        return services

    @rpc
    def close_all_instance(self, service_name):
        LOGGER.info(f"close all instance: {service_name}")
        self.dispatch(f"{service_name}close_event", service_name)

    @rpc
    def close_one_instance(self, service_name):
        LOGGER.info(f"close one instance: {service_name}")
        close_unique_id = str(uuid.uuid4())
        self.dispatch(f"{service_name}close_one_event", close_unique_id)

    @rpc
    def run_service(self, service_name):
        module_name = service_name.replace("_service", "")
        LOGGER.info(f"start a {module_name} instance...")
        plat = platform.system().lower()
        if plat == 'linux':
            if module_name == 'detection':
                module_name += '_hx'
            elif module_name == 'track':
                module_name += '_hx'
        # 获取当前工作目录
        current_directory = os.getcwd()
        # 获取当前环境变量
        current_env = os.environ.copy()
        current_env["PYTHONPATH"] = current_directory

        if plat == 'windows':
            subprocess.Popen(["start", "nameko", "run", '--config', 'nameko_config.yaml',
                              f"microservice.{module_name}:{service_name.title().replace('_', '')}"],
                             shell=True, env=current_env)
        elif plat == 'linux':
            subprocess.Popen(["nohup", "nameko", "run", '--config', 'nameko_config.yaml',
                              f"microservice.{module_name}:{service_name.title().replace('_', '')}"],
                             env=current_env)
        else:
            raise NotImplementedError(f"暂不支持{plat}平台")

