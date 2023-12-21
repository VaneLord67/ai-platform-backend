from flask import request, Blueprint

from common.api_response import APIResponse
from model.service_info import ServiceInfo
from .singleton import rpc

model_manage_bp = Blueprint('model_manage', __name__, url_prefix='/model/manage')


@model_manage_bp.route('/service/list', methods=['GET'])
def get_service_list():
    service_name = request.args.get("serviceName")
    service_strs = rpc.manage_service.get_services(service_name)
    services = []
    for service_str in service_strs:
        services.append(ServiceInfo().from_json(service_str))
    response = APIResponse.success_with_data(services)
    response.to_dict()
    return response.to_dict()


@model_manage_bp.route('/service/stop_all', methods=['POST'])
def stop_all_service():
    json_dict = request.get_json()
    service_name = json_dict['serviceName']
    rpc.manage_service.close_all_instance(service_name)
    return APIResponse.success().to_dict()


@model_manage_bp.route('/service/stop', methods=['POST'])
def stop_one_service():
    json_dict = request.get_json()
    service_name = json_dict['serviceName']
    rpc.manage_service.close_one_instance(service_name)
    return APIResponse.success().to_dict()


@model_manage_bp.route('/service/start', methods=['POST'])
def start_service():
    json_dict = request.get_json()
    service_name = json_dict['serviceName']
    rpc.manage_service.run_service(service_name)
    return APIResponse.success().to_dict()
