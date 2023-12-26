import uuid

from flask import request, Blueprint

from common.api_response import APIResponse
from microservice.recognition import RecognitionService
from model.cls_result import ClsResult
from model.support_input import CAMERA_TYPE
from .singleton import rpc, socketio, register_route
from .socketio_namespace import DynamicNamespace

url_prefix = "/model/recognition"
recognition_bp = Blueprint('recognition', __name__, url_prefix=url_prefix)


@recognition_bp.route('/call', methods=['POST'])
@register_route(url_prefix + "/call", "调用分类服务", "POST")
def call():
    json_data = request.get_json()
    if json_data['supportInput']['type'] == CAMERA_TYPE:
        unique_id = str(uuid.uuid4())
        namespace = '/' + unique_id
        dynamicNamespace = DynamicNamespace(namespace, unique_id, service_name=RecognitionService.name)
        json_data['stopSignalKey'] = dynamicNamespace.stop_signal_key
        json_data['queueName'] = dynamicNamespace.queue_name
        json_data['logKey'] = dynamicNamespace.log_key
        output: dict = rpc.recognition_service.call(json_data)
        service_unique_id = output['unique_id']
        dynamicNamespace.service_unique_id = service_unique_id
        socketio.on_namespace(dynamicNamespace)
        return APIResponse.success_with_data(namespace).flask_response()
    else:
        output_dict: dict = rpc.recognition_service.call(json_data)
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
