import json
import uuid

from flask import request, Blueprint

from common.api_response import APIResponse
from model.detection_output import DetectionOutput
from model.support_input import CAMERA_TYPE
from . import const
from .singleton import rpc, socketio
from .socketio_namespace import DynamicNamespace

detection_bp = Blueprint('detection', __name__, url_prefix='/model/detection')


@detection_bp.route('/call', methods=['POST'])
def call():
    json_data = request.get_json()
    if json_data['supportInput']['type'] == CAMERA_TYPE:
        unique_id = str(uuid.uuid4())
        namespace = '/' + unique_id
        # threading.Thread(target=rpc.detection_service.detectRPCHandler, args=[json_data]).start()
        dynamicNamespace = DynamicNamespace(namespace, unique_id)
        json_data['stopSignalKey'] = dynamicNamespace.stop_signal_key
        json_data['queueName'] = dynamicNamespace.queue_name
        output: str = rpc.detection_service.detectRPCHandler(json_data)
        service_unique_id = json.loads(output)['unique_id']
        dynamicNamespace.service_unique_id = service_unique_id
        socketio.on_namespace(dynamicNamespace)
        return APIResponse.success_with_data(namespace).flask_response()
    else:
        output_dict = rpc.detection_service.detectRPCHandler(json_data)
        output: DetectionOutput = DetectionOutput().from_json(output_dict)
        response: APIResponse
        if len(output.urls) == 0:
            response = APIResponse.fail()
        else:
            response = APIResponse.success_with_data(output)
        return response.flask_response()


@detection_bp.route('/imgSrc', methods=['GET'])
def get_img_src():
    return APIResponse.success_with_data(const.global_img_src).flask_response()
