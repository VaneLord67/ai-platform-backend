from common.util import JsonBase
from model.ai_model import AIModel

ServiceReadyState = "ready"
ServiceRunningState = "running"


class ServiceInfo(JsonBase):
    def __init__(self):
        super().__init__()
        self.state: str = ServiceReadyState
        self.model: AIModel = AIModel()

    def __json__(self):
        return self.__str__()
