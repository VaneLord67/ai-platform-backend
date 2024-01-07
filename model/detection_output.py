from typing import List

from common.util import JsonBase
from model.box import Box


class DetectionOutput(JsonBase):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.frames: List[List[Box]] = []
        self.logs: List[str] = []
        self.busy: bool = False

    def __json__(self):
        return self.__str__()
