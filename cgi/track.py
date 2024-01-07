import uuid

from flask import request, Blueprint

from common.api_response import APIResponse
from common.error_code import ErrorCodeEnum
from microservice.track import TrackService
from model.box import Box
from model.support_input import CAMERA_TYPE
from .singleton import rpc, socketio, register_route
from .socketio_namespace import DynamicNamespace

url_prefix = '/model/track'
track_bp = Blueprint('track', __name__, url_prefix=url_prefix)


@track_bp.route('/call', methods=['POST'])
@register_route(url_prefix + "/call", "调用跟踪服务", "POST")
def call():
    json_data = request.get_json()
    call_cnt = 0
    if json_data['supportInput']['type'] == CAMERA_TYPE:
        unique_id = str(uuid.uuid4())
        namespace = '/' + unique_id
        dynamicNamespace = DynamicNamespace(namespace, unique_id, service_name=TrackService.name)
        json_data['stopSignalKey'] = dynamicNamespace.stop_signal_key
        json_data['queueName'] = dynamicNamespace.queue_name
        json_data['roiKey'] = dynamicNamespace.roi_key
        json_data['logKey'] = dynamicNamespace.log_key
        output_dict: dict = rpc.track_service.track(json_data)
        while output_dict is None:
            output_dict = rpc.track_service.track(json_data)
            call_cnt += 1
            if call_cnt >= 10:
                return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.SERVICE_BUSY_ERROR).flask_response()
        service_unique_id = output_dict['unique_id']
        dynamicNamespace.service_unique_id = service_unique_id
        socketio.on_namespace(dynamicNamespace)
        return APIResponse.success_with_data(namespace).flask_response()
    else:
        output_dict: dict = rpc.track_service.track(json_data)
        while output_dict is None:
            output_dict = rpc.track_service.track(json_data)
            call_cnt += 1
            if call_cnt >= 10:
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


@track_bp.route('/first_frame', methods=['GET'])
@register_route(url_prefix + "/first_frame", "获取视频第一帧", "GET")
def get_first_frame():
    url = request.args.get('url')
    jpg_base64_text = rpc.track_service.get_first_frame(url)
    return APIResponse.success_with_data(jpg_base64_text).flask_response()



