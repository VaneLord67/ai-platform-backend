import socket

import psutil
from GPUtil import GPUtil
from nameko.extensions import DependencyProvider


class LoadDependency(DependencyProvider):

    def __init__(self):
        pass

    def setup(self):
        pass

    def get_dependency(self, worker_ctx):
        return self

    def get_load(self):
        gpus = GPUtil.getGPUs()
        gpu_percent = [gpu.load for gpu in gpus]
        load = {
            'hostname': socket.gethostname(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "gpu_percent": gpu_percent
        }
        return load
