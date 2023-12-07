from flask import request, Blueprint

from common.api_response import APIResponse
from model.service_info import ServiceInfo
from .singleton import rpc

model_manage_bp = Blueprint('model_manage', __name__, url_prefix='/model/manage')


@model_manage_bp.route('/service/detection/list', methods=['GET'])
def get_detection_service_list():
    json_data = request.get_json()
    service_strs = rpc.manage_service.get_detection_services()
    services = []
    for service_str in service_strs:
        services.append(ServiceInfo().from_json(service_str))
    response = APIResponse.success_with_data(services)
    response.to_dict()
    return response.to_dict()
