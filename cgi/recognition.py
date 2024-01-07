import uuid

from flask import request, Blueprint

from common.api_response import APIResponse
from common.error_code import ErrorCodeEnum
from microservice.recognition import RecognitionService
from model.cls_result import ClsResult
from model.support_input import CAMERA_TYPE, VIDEO_URL_TYPE
from .singleton import rpc, socketio, register_route
from .socketio_namespace import DynamicNamespace

url_prefix = "/model/recognition"
recognition_bp = Blueprint('recognition', __name__, url_prefix=url_prefix)


def recall(json_data, max_call_times=10):
    call_cnt = 0
    output_dict: dict = rpc.recognition_service.call(json_data)
    while output_dict['busy']:
        output_dict: dict = rpc.recognition_service.call(json_data)
        call_cnt += 1
        if call_cnt >= max_call_times:
            return None
    return output_dict


def async_call(json_data, namespace, dynamicNamespace, max_call_times=10):
    output_dict: dict = recall(json_data, max_call_times)
    if output_dict is None:
        return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.SERVICE_BUSY_ERROR).flask_response()
    service_unique_id = output_dict['unique_id']
    dynamicNamespace.service_unique_id = service_unique_id
    socketio.on_namespace(dynamicNamespace)
    return APIResponse.success_with_data(namespace).flask_response()


@recognition_bp.route('/call', methods=['POST'])
@register_route(url_prefix + "/call", "调用分类服务", "POST")
def call():
    json_data = request.get_json()
    if json_data['supportInput']['type'] in [CAMERA_TYPE, VIDEO_URL_TYPE]:
        source = json_data['supportInput']['type']
        unique_id = str(uuid.uuid4())
        namespace = '/' + unique_id
        dynamicNamespace = DynamicNamespace(namespace, unique_id,
                                            service_name=RecognitionService.name,
                                            source=source)
        json_data = dynamicNamespace.set_json_data(json_data)
        return async_call(json_data, namespace, dynamicNamespace)
    else:
        output_dict: dict = recall(json_data)
        if output_dict is None:
            return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.SERVICE_BUSY_ERROR).flask_response()
        frame_strs = output_dict['frames']
        logs = output_dict['logs']
        frames = []
        for frame_str in frame_strs:
            frames.append(ClsResult().from_json(frame_str))
        data = {
            'frames': frames,
            'logs': logs,
        }
        response: APIResponse
        if len(frames) == 0:
            response = APIResponse.fail()
        else:
            response = APIResponse.success_with_data(data)
        return response.flask_response()
