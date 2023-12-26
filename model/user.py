from common.util import JsonBase


class User(JsonBase):
    def __init__(self, id=None, username=None, password=None, role=None):
        super().__init__()
        self.id: int = id
        self.username: str = username
        self.password: str = password
        self.role: str = role

    def __json__(self):
        return self.__str__()