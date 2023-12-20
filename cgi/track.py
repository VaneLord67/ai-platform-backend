import json
import uuid

from flask import request, Blueprint
from flask_socketio import SocketIO

from common.api_response import APIResponse
from model.support_input import CAMERA_TYPE
from model.track_result import TrackResult
from .singleton import rpc
from .socketio_namespace import DynamicNamespace

track_bp = Blueprint('track', __name__, url_prefix='/model/track')
track_socketio = SocketIO()


@track_bp.route('/call', methods=['POST'])
def call():
    json_data = request.get_json()
    if json_data['supportInput']['type'] == CAMERA_TYPE:
        unique_id = str(uuid.uuid4())
        namespace = '/' + unique_id
        dynamicNamespace = DynamicNamespace(namespace, unique_id)
        json_data['stopSignalKey'] = dynamicNamespace.stop_signal_key
        json_data['queueName'] = dynamicNamespace.queue_name
        output: str = rpc.detection_service.detectRPCHandler(json_data)
        service_unique_id = json.loads(output)['unique_id']
        dynamicNamespace.service_unique_id = service_unique_id
        track_socketio.on_namespace(dynamicNamespace)
        return APIResponse.success_with_data(namespace).flask_response()
    else:
        output_dict: dict = rpc.track_service.track(json_data)
        url = output_dict['url']
        frame_strs = output_dict['frames']
        frames = []
        for frame_str in frame_strs:
            frames.append(TrackResult().from_json(frame_str))
        data = {
            'frames': frames,
            'url': url,
        }
        response: APIResponse
        if len(url) == 0:
            response = APIResponse.fail()
        else:
            response = APIResponse.success_with_data(data)
        return response.flask_response()


@track_bp.route('/first_frame', methods=['GET'])
def get_first_frame():
    url = request.args.get('url')
    jpg_base64_text = rpc.track_service.get_first_frame(url)
    return APIResponse.success_with_data(jpg_base64_text).flask_response()



