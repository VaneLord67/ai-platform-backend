from common.util import JsonBase


class ClsResult(JsonBase):
    def __init__(self, label=None, class_name=None, confidence=None):
        super().__init__()
        self.label: int = label
        self.class_name: str = class_name
        self.confidence: float = confidence

    def __json__(self):
        return self.__str__()
