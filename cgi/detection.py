import json
import uuid

from flask import request, Blueprint

from common.api_response import APIResponse
from common.error_code import ErrorCodeEnum
from microservice.detection import DetectionService
from model.detection_output import DetectionOutput
from model.support_input import CAMERA_TYPE, VIDEO_URL_TYPE
from .singleton import rpc, socketio, register_route
from .socketio_namespace import DynamicNamespace

url_prefix = "/model/detection"
detection_bp = Blueprint('detection', __name__, url_prefix=url_prefix)


def recall(json_data, max_call_times=10):
    call_cnt = 0
    output: str = rpc.detection_service.detectRPCHandler(json_data)
    output_obj: DetectionOutput = DetectionOutput().from_json(output)
    while output_obj.busy:
        output = rpc.detection_service.detectRPCHandler(json_data)
        output_obj: DetectionOutput = DetectionOutput().from_json(output)
        call_cnt += 1
        if call_cnt >= max_call_times:
            return None
    return output


def async_call(json_data, namespace, dynamicNamespace, max_call_times=10):
    output: str = recall(json_data, max_call_times)
    if output is None:
        return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.SERVICE_BUSY_ERROR).flask_response()
    service_unique_id = json.loads(output)['unique_id']
    dynamicNamespace.service_unique_id = service_unique_id
    socketio.on_namespace(dynamicNamespace)
    return APIResponse.success_with_data(namespace).flask_response()


@detection_bp.route('/call', methods=['POST'])
@register_route(url_prefix + "/call", "检测服务调用", "POST")
def call():
    json_data = request.get_json()
    if json_data['supportInput']['type'] == CAMERA_TYPE:
        unique_id = str(uuid.uuid4())
        namespace = '/' + unique_id
        dynamicNamespace = DynamicNamespace(namespace, unique_id,
                                            service_name=DetectionService.name, source=CAMERA_TYPE)
        json_data['stopSignalKey'] = dynamicNamespace.stop_signal_key
        json_data['queueName'] = dynamicNamespace.queue_name
        json_data['logKey'] = dynamicNamespace.log_key
        return async_call(json_data, namespace, dynamicNamespace)
    elif json_data['supportInput']['type'] == VIDEO_URL_TYPE:
        unique_id = str(uuid.uuid4())
        namespace = '/' + unique_id
        dynamicNamespace = DynamicNamespace(namespace, unique_id,
                                            service_name=DetectionService.name,
                                            source=VIDEO_URL_TYPE)
        json_data['stopSignalKey'] = dynamicNamespace.stop_signal_key
        json_data['logKey'] = dynamicNamespace.log_key
        json_data['videoProgressKey'] = dynamicNamespace.video_progress_key
        json_data['taskId'] = dynamicNamespace.unique_id
        return async_call(json_data, namespace, dynamicNamespace)
    else:
        output: str = recall(json_data)
        if output is None:
            return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.SERVICE_BUSY_ERROR).flask_response()
        output: DetectionOutput = DetectionOutput().from_json(output)
        response: APIResponse
        if len(output.urls) == 0 and len(output.logs) == 0:
            response = APIResponse.fail()
        else:
            response = APIResponse.success_with_data(output)
        return response.flask_response()
