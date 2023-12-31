from enum import Enum


class ErrorCode:

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class ErrorCodeEnum(Enum):
    UNSUPPORTED_INPUT_ERROR = ErrorCode(501, "不支持的输入形式")
    SERVICE_BUSY_ERROR = ErrorCode(502, "服务忙碌，请稍后再试")
    ARGUMENT_ERROR = ErrorCode(401, "参数异常")
    AUTH_ERROR = ErrorCode(403, "权限不足")
