from datetime import datetime

from common.util import JsonBase


class Task(JsonBase):
    def __init__(self, task_id=None, user_id=None, username=None, path=None, time=None, input_mode=None):
        super().__init__()
        self.task_id: str = task_id if task_id else ""
        self.user_id: int = user_id if user_id else -1
        self.username: str = username if username else ""
        self.path: str = path if path else ""
        self.time: datetime = time if time else None
        self.input_mode: str = input_mode if input_mode else ""

    def __json__(self):
        return self.__str__()
