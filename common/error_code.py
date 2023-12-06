from enum import Enum


class ErrorCode:

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class ErrorCodeEnum(Enum):
    UNSUPPORTED_INPUT_ERROR = ErrorCode(501, "不支持的输入形式")
