from datetime import datetime

from common.util import JsonBase


class RequestLog(JsonBase):
    def __init__(self, id=None, user_id=None, method=None,
                 path=None, status_code=None, duration=None,
                 response_json=None, time=None):
        super().__init__()
        self.id: int = id if id else 0
        self.user_id: int = user_id if user_id else 0
        self.method: str = method if method else ""
        self.path: str = path if path else ""
        self.status_code: int = status_code if status_code else 0
        self.duration: float = duration if duration else 0
        self.response_json: str = response_json if response_json else ""
        self.time: int = time if time else 0

    def __json__(self):
        return self.__str__()