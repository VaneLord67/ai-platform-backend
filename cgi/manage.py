from flask import request, Blueprint

from common.api_response import APIResponse
from model.service_info import ServiceInfo
from .singleton import rpc

model_manage_bp = Blueprint('model_manage', __name__, url_prefix='/model/manage')


@model_manage_bp.route('/service/detection/list', methods=['GET'])
def get_detection_service_list():
    service_strs = rpc.manage_service.get_detection_services()
    services = []
    for service_str in service_strs:
        services.append(ServiceInfo().from_json(service_str))
    response = APIResponse.success_with_data(services)
    response.to_dict()
    return response.to_dict()


@model_manage_bp.route('/service/detection/stop_all', methods=['POST'])
def stop_all_detection_service():
    service_name = "detection_service"
    rpc.manage_service.close_all_instance(service_name)
    return APIResponse.success().to_dict()


@model_manage_bp.route('/service/detection/stop', methods=['POST'])
def stop_one_detection_service():
    service_name = "detection_service"
    rpc.manage_service.close_one_instance(service_name)
    return APIResponse.success().to_dict()


@model_manage_bp.route('/service/detection/start', methods=['POST'])
def start_detection_service():
    service_name = "detection_service"
    rpc.manage_service.run_service(service_name)
    return APIResponse.success().to_dict()
