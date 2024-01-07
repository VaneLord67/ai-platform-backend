import uuid

from flask import request, Blueprint

from common.api_response import APIResponse
from common.error_code import ErrorCodeEnum
from microservice.track import TrackService
from model.box import Box
from model.support_input import CAMERA_TYPE, VIDEO_URL_TYPE
from .ai_common import async_call, recall
from .singleton import rpc, socketio, register_route
from .socketio_namespace import DynamicNamespace

url_prefix = '/model/track'
track_bp = Blueprint('track', __name__, url_prefix=url_prefix)


def call_function(json_data):
    return rpc.track_service.call(json_data)


def busy_check_function(output):
    return output['busy']


@track_bp.route('/call', methods=['POST'])
@register_route(url_prefix + "/call", "调用跟踪服务", "POST")
def call():
    json_data = request.get_json()
    if json_data['supportInput']['type'] in [CAMERA_TYPE, VIDEO_URL_TYPE]:
        source, namespace, unique_id = DynamicNamespace.init_parameter(json_data)
        dynamicNamespace = DynamicNamespace(namespace, unique_id,
                                            service_name=TrackService.name,
                                            source=source,
                                            )
        json_data = dynamicNamespace.set_json_data(json_data)
        return async_call(call_function, busy_check_function, json_data, namespace, dynamicNamespace)
    else:
        output_dict: dict = recall(call_function, busy_check_function, json_data)
        if output_dict is None:
            return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.SERVICE_BUSY_ERROR).flask_response()
        url = output_dict['url']
        frame_strs = output_dict['frames']
        logs = output_dict['logs']
        frames = []
        for frame_str in frame_strs:
            boxes = []
            for box_dict in frame_str:
                if box_dict['track_id'] > 0:
                    boxes.append(Box().from_dict(box_dict))
            frames.append(boxes)
        data = {
            'frames': frames,
            'url': url,
            'logs': logs,
        }
        response: APIResponse
        if len(url) == 0:
            response = APIResponse.fail()
        else:
            response = APIResponse.success_with_data(data)
        return response.flask_response()
