from flask import request, Blueprint

from common.api_response import APIResponse
from common.error_code import ErrorCodeEnum
from microservice.detection import DetectionService
from model.detection_output import DetectionOutput
from model.support_input import CAMERA_TYPE, VIDEO_URL_TYPE
from .ai_common import async_call, recall
from .singleton import rpc, register_route
from .socketio_namespace import DynamicNamespace

url_prefix = "/model/detection"
detection_bp = Blueprint('detection', __name__, url_prefix=url_prefix)


def call_function(json_data):
    return rpc.detection_service.call(json_data)


def busy_check_function(output):
    output_obj: DetectionOutput = DetectionOutput().from_json(output)
    return output_obj.busy


@detection_bp.route('/call', methods=['POST'])
@register_route(url_prefix + "/call", "检测服务调用", "POST")
def call():
    json_data = request.get_json()
    if json_data['supportInput']['type'] in [CAMERA_TYPE, VIDEO_URL_TYPE]:
        source, namespace, unique_id = DynamicNamespace.init_parameter(json_data)
        dynamicNamespace = DynamicNamespace(namespace, unique_id,
                                            service_name=DetectionService.name, source=source)
        json_data = dynamicNamespace.set_json_data(json_data)
        return async_call(call_function, busy_check_function, json_data, namespace, dynamicNamespace)
    else:
        output: str = recall(call_function, busy_check_function, json_data)
        if output is None:
            return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.SERVICE_BUSY_ERROR).flask_response()
        output: DetectionOutput = DetectionOutput().from_json(output)
        response: APIResponse
        if len(output.urls) == 0 and len(output.logs) == 0:
            response = APIResponse.fail()
        else:
            response = APIResponse.success_with_data(output)
        return response.flask_response()
