from common.util import JsonBase

SINGLE_PICTURE_URL_TYPE = "single_picture_url"
MULTIPLE_PICTURE_URL_TYPE = "multiple_picture_url"
VIDEO_URL_TYPE = "video_url"
CAMERA_TYPE = "camera"


class SupportInput(JsonBase):
    def __init__(self):
        super().__init__()
        self.type: str = ""
        self.format: str = ""
        self.value: any = ""

    def __json__(self):
        return self.to_json()
