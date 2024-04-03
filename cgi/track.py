from flask import request, Blueprint

from common.api_response import APIResponse
from common.error_code import ErrorCodeEnum
from .ai_common import async_call, if_async_call_type, default_busy_check_function
from .singleton import rpc, register_route
from .socketio_namespace import DynamicNamespace

url_prefix = '/model/track'
track_bp = Blueprint('track', __name__, url_prefix=url_prefix)


def call_function(json_data):
    return rpc.track_service.call(json_data)


@track_bp.route('/call', methods=['POST'])
@register_route(url_prefix + "/call", "调用跟踪服务", "POST")
def call():
    json_data = request.get_json()
    if if_async_call_type(json_data):
        source, namespace, unique_id = DynamicNamespace.init_parameter(json_data)
        dynamicNamespace = DynamicNamespace(namespace, unique_id,
                                            service_name="track_service",
                                            source=source,
                                            )
        json_data = dynamicNamespace.set_json_data(json_data)
        return async_call(call_function, default_busy_check_function, json_data, namespace, dynamicNamespace)
    else:
        return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.UNSUPPORTED_INPUT_ERROR).flask_response()
