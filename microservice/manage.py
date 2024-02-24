import platform
import subprocess
import time
import uuid

from nameko.events import EventDispatcher
from nameko.rpc import rpc

from common.log import LOGGER
from microservice.load_dependency import LoadDependency
from microservice.mysql_storage import MysqlStorage
from microservice.redis_storage import RedisStorage
from model.service_info import ServiceInfo


class ManageService:
    name = "manage_service"

    dispatch = EventDispatcher()
    redis_storage = RedisStorage()
    mysql_storage = MysqlStorage()
    load_dependency = LoadDependency()

    @rpc
    def get_load(self):
        load = self.load_dependency.get_load()
        return load

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
        if plat == 'windows':
            subprocess.Popen(["start", "nameko", "run", '--config', 'nameko_config.yaml',
                              f"microservice.{module_name}:{service_name.title().replace('_', '')}"],
                             shell=True)
        elif plat == 'linux':
            subprocess.Popen(["nohup", "nameko", "run", '--config', 'nameko_config.yaml',
                              f"microservice.{module_name}:{service_name.title().replace('_', '')}"])
        else:
            raise NotImplementedError(f"暂不支持{plat}平台")

