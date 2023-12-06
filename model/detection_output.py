from common.util import JsonBase


class DetectionOutput(JsonBase):
    def __init__(self):
        super().__init__()
        self.url: str = ""

    def __json__(self):
        return self.to_json()