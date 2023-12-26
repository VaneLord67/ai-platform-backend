import uuid

from flask import request, Blueprint

from common.api_response import APIResponse
from microservice.track import TrackService
from model.support_input import CAMERA_TYPE
from model.track_result import TrackResult
from .singleton import rpc, socketio, register_route
from .socketio_namespace import DynamicNamespace

url_prefix = '/model/track'
track_bp = Blueprint('track', __name__, url_prefix=url_prefix)


@track_bp.route('/call', methods=['POST'])
@register_route(url_prefix + "/call", "调用跟踪服务", "POST")
def call():
    json_data = request.get_json()
    if json_data['supportInput']['type'] == CAMERA_TYPE:
        unique_id = str(uuid.uuid4())
        namespace = '/' + unique_id
        dynamicNamespace = DynamicNamespace(namespace, unique_id, service_name=TrackService.name)
        json_data['stopSignalKey'] = dynamicNamespace.stop_signal_key
        json_data['queueName'] = dynamicNamespace.queue_name
        json_data['roiKey'] = dynamicNamespace.roi_key
        json_data['logKey'] = dynamicNamespace.log_key
        output_dict: dict = rpc.track_service.track(json_data)
        service_unique_id = output_dict['unique_id']
        dynamicNamespace.service_unique_id = service_unique_id
        socketio.on_namespace(dynamicNamespace)
        return APIResponse.success_with_data(namespace).flask_response()
    else:
        output_dict: dict = rpc.track_service.track(json_data)
        url = output_dict['url']
        frame_strs = output_dict['frames']
        logs = output_dict['logs']
        frames = []
        for frame_str in frame_strs:
            frames.append(TrackResult().from_json(frame_str))
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



