from common.util import JsonBase


class User(JsonBase):
    def __init__(self):
        super().__init__()
        self.id: int = 0
        self.username: str = ""
        self.password: str = ""

    def __json__(self):
        return self.__str__()