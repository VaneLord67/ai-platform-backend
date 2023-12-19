from common.util import JsonBase


class TrackResult(JsonBase):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.x: int = x
        self.y: int = y
        self.width: int = width
        self.height: int = height

    def __json__(self):
        return self.__str__()
