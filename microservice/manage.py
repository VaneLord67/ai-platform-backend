import subprocess
import time

from nameko.events import EventDispatcher
from nameko.rpc import rpc

from microservice.redis_storage import RedisStorage
from model.service_info import ServiceInfo


class ManageService:
    name = "manage_service"

    dispatch = EventDispatcher()
    redis_storage = RedisStorage()

    @rpc
    def get_detection_services(self):
        services = []
        service_list_key = "detection_service_info"
        self.redis_storage.client.delete(service_list_key)
        service_name = "detection_service"
        self.dispatch(f"{service_name}state_report", service_list_key)
        time.sleep(0.5)
        list_elements = self.redis_storage.client.lrange(service_list_key, 0, -1)
        for service_info_str in list_elements:
            serviceInfo = ServiceInfo().from_json(service_info_str)
            services.append(serviceInfo)
        return services


    @rpc
    def hello(self):
        return "hello!"

    @rpc
    def close_all_instance(self, service_name):
        print(f"close all instance: {service_name}")
        self.dispatch(f"{service_name}close_event", service_name)

    @rpc
    def run_service(self, service_name):
        service_name = service_name.replace("_service", "")
        print(f"start a {service_name} instance...")
        subprocess.Popen(["start", "nameko", "run", f"microservice.{service_name}"], shell=True)
        # subprocess.Popen([r"D:\Anaconda3\envs\ai-platform\python.exe", r"microservice\demo.py"],
        #                  stdout=subprocess.DEVNULL)
