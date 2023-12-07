from common.util import JsonBase


class Hyperparameter(JsonBase):
    def __init__(self):
        super().__init__()
        self.type: str = ""
        self.name: str = ""
        self.value: str = ""

    def __json__(self):
        return self.to_json()
