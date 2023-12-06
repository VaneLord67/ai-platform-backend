import eventlet
eventlet.monkey_patch()
from nameko.web.handlers import http
from werkzeug import Request

from common.api_response import APIResponse
from common.error_code import ErrorCodeEnum
from common.util import connect_to_database
from model.detection_output import DetectionOutput
from model.hyperparameter import Hyperparameter
from model.support_input import SupportInput, SINGLE_PICTURE_URL_TYPE


class DetectionService:
    name = "detection_service"

    def __init__(self):
        self.conn = connect_to_database()

    @http('POST', '/model/detect')
    def hello(self, request: Request):
        json_data = request.get_json()
        hyperparameter = Hyperparameter().from_dict(json_data['hyperparameter']) \
            if 'hyperparameter' in json_data else Hyperparameter()
        supportInput = SupportInput().from_dict(json_data['support_input'])
        if supportInput.type == SINGLE_PICTURE_URL_TYPE:
            output = DetectionOutput()
            output.url = "https://img2.baidu.com/it/u=2933220116,3086945787&fm=253&fmt=auto&app=138&f=JPEG?w=744&h=500"
            return APIResponse.success_with_data(output).__str__()
        return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.UNSUPPORTED_INPUT_ERROR)