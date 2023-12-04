import subprocess

from nameko.events import EventDispatcher
from nameko.rpc import rpc


class ManageService:
    name = "manage_service"

    dispatch = EventDispatcher()

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
