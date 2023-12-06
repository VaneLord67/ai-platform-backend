from common.util import JsonBase


class AIService(JsonBase):
    def __init__(self):
        super().__init__()
        self.model_id: int = 0
        self.state: str = "running"
        self.host_name: str = ""
        self.ip_address: str = ""
        self.gpu_usage: int = 0
        self.cpu_usage: int = 0
        self.memory_usage: int = 0

    def __json__(self):
        return self.to_json()
