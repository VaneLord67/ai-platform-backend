from flask import request, Blueprint

from common.api_response import APIResponse
from common.error_code import ErrorCodeEnum
from model.detection_output import DetectionOutput
from .ai_common import async_call, recall, default_busy_check_function, if_async_call_type
from .singleton import rpc, register_route
from .socketio_namespace import DynamicNamespace

url_prefix = "/model/detection"
detection_bp = Blueprint('detection', __name__, url_prefix=url_prefix)


def call_function(json_data):
    return rpc.detection_service.call(json_data)


@detection_bp.route('/call', methods=['POST'])
@register_route(url_prefix + "/call", "检测服务调用", "POST")
def call():
    json_data = request.get_json()
    if if_async_call_type(json_data):
        source, namespace, unique_id = DynamicNamespace.init_parameter(json_data)
        dynamicNamespace = DynamicNamespace(namespace, unique_id,
                                            service_name="detection_service", source=source)
        json_data = dynamicNamespace.set_json_data(json_data)
        return async_call(call_function, default_busy_check_function, json_data, namespace, dynamicNamespace)
    else:
        output: dict = recall(call_function, default_busy_check_function, json_data)
        if output is None:
            return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.SERVICE_BUSY_ERROR).flask_response()
        response: APIResponse
        detection_output = DetectionOutput().from_dict(output)
        if len(detection_output.urls) == 0 and len(detection_output.logs) == 0:
            response = APIResponse.fail()
        else:
            response = APIResponse.success_with_data(detection_output)
        return response.flask_response()
