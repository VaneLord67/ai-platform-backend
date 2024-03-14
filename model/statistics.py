from common.util import JsonBase


class Statistics(JsonBase):
    def __init__(self, path=None, total_calls=None,
                 average_response_time=None,
                 max_response_time=None,
                 error_rate=None):
        super().__init__()
        self.path: str = path
        self.total_calls: int = total_calls
        self.average_response_time: float = average_response_time
        self.max_response_time: float = max_response_time
        self.error_rate: float = error_rate

    def __json__(self):
        return self.__str__()