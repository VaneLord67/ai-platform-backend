from common.util import JsonBase


class RequestLog(JsonBase):
    def __init__(self):
        super().__init__()
        self.id: int = 0
        self.user_id: int = 0
        self.method: str = ""
        self.path: str = ""
        self.status_code: int = 0
        self.duration: float = 0
        self.response_json: str = ""

    def __json__(self):
        return self.__str__()