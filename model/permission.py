from common.util import JsonBase


class Permission(JsonBase):
    def __init__(self, role=None, route=None, act=None, description=None):
        super().__init__()
        self.role: str = role
        self.route: str = route
        self.act: str = act
        self.description: str = description

    def __json__(self):
        return self.__str__()
