import json

from flask import request, Blueprint

from common.api_response import APIResponse
from model.detection_output import DetectionOutput
from .singleton import rpc

detection_bp = Blueprint('detection', __name__, url_prefix='/model/detection')


@detection_bp.route('/call', methods=['POST'])
def call():
    output_dict = rpc.detection_service.detectRPCHandler(request.get_json())
    output: DetectionOutput = DetectionOutput().from_json(output_dict)
    response: APIResponse
    if len(output.urls) == 0:
        response = APIResponse.fail()
    else:
        response = APIResponse.success_with_data(output)
    return json.loads(response.__str__())

