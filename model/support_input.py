from common.util import JsonBase

SINGLE_PICTURE_URL_TYPE = "single_picture_url"
MULTIPLE_PICTURE_URL_TYPE = "multiple_picture_url"
PICTURE_STREAM_TYPE = "picture_stream"
VIDEO_URL_TYPE = "video_url"


class SupportInput(JsonBase):
    def __init__(self):
        super().__init__()
        self.type: str = ""
        self.format: str = ""
        self.value: str = ""

    def __json__(self):
        return self.to_json()
