from typing import List

from common.util import JsonBase
from model.hyperparameter import Hyperparameter
from model.support_input import SupportInput


class AIModel(JsonBase):
    def __init__(self):
        super().__init__()
        # self.id: int = 0
        self.name: str = ""
        self.field: str = ""
        self.hyperparameters: List[Hyperparameter] = []
        self.support_input: List[SupportInput] = []

    def __json__(self):
        return self.to_json()