from enum import Enum


class CameraModeEnum(Enum):
    WEBRTC_STREAMER = "webrtc-streamer"
    PYTHON_PUBLISH_STREAM = "python端推流"
    SEI = "SEI"
