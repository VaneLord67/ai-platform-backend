import time

from common.util import JsonBase, get_hostname
from model.ai_model import AIModel

ServiceReadyState = "ready"
ServiceRunningState = "running"


class ServiceInfo(JsonBase):
    def __init__(self):
        super().__init__()
        self.state: str = ServiceReadyState
        self.task_start_time: int = int(time.time() * 1000)
        self.hostname: str = get_hostname()
        self.task_type: str = ""

        self.model: AIModel = AIModel()

    def __json__(self):
        return self.__str__()
