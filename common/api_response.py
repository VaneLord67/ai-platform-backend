import json

from common.error_code import ErrorCode, ErrorCodeEnum
from common.util import JsonBase


class APIResponse(JsonBase):
    def __init__(self, code, message, data=None):
        super().__init__()
        self.code = code
        self.message = message
        self.data = data

    def to_dict(self):
        return {'code': self.code, 'message': self.message, 'data': self.data}

    @staticmethod
    def success():
        return APIResponse(code=1, message="success")

    @staticmethod
    def success_with_data(data):
        return APIResponse(code=1, message="success", data=data)

    @staticmethod
    def fail():
        return APIResponse(code=0, message="fail")

    @staticmethod
    def fail_with_error_code(error_code: ErrorCode):
        return APIResponse(code=error_code.code, message=error_code.message)

    @staticmethod
    def fail_with_error_code_enum(error_code_enum: ErrorCodeEnum):
        error_code: ErrorCode = error_code_enum.value
        return APIResponse(code=error_code.code, message=error_code.message)