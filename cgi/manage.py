import time

from flask import request, Blueprint

from common.api_response import APIResponse
from model.service_info import ServiceInfo
from .singleton import rpc, register_route

url_prefix = "/model/manage"
model_manage_bp = Blueprint('model_manage', __name__, url_prefix='/model/manage')


@model_manage_bp.route('/service/list', methods=['GET'])
@register_route(url_prefix + "/service/list", "获取服务列表", "GET")
def get_service_list():
    service_name = request.args.get("serviceName")
    service_strs = rpc.manage_service.get_services(service_name)
    services = []
    for service_str in service_strs:
        services.append(ServiceInfo().from_json(service_str))
    response = APIResponse.success_with_data(services)
    return response.to_dict()


@model_manage_bp.route('/service/stop_all', methods=['POST'])
@register_route(url_prefix + "/service/stop_all", "停止所有服务实例", "POST")
def stop_all_service():
    json_dict = request.get_json()
    service_name = json_dict['serviceName']
    rpc.manage_service.close_all_instance(service_name)
    return APIResponse.success().to_dict()


@model_manage_bp.route('/service/stop', methods=['POST'])
@register_route(url_prefix + "/service/stop", "停止一个服务实例", "POST")
def stop_one_service():
    json_dict = request.get_json()
    service_name = json_dict['serviceName']
    rpc.manage_service.close_one_instance(service_name)
    return APIResponse.success().to_dict()


@model_manage_bp.route('/service/start', methods=['POST'])
@register_route(url_prefix + "/service/start", "启动一个服务实例", "POST")
def start_service():
    json_dict = request.get_json()
    service_name = json_dict['serviceName']
    rpc.manage_service.run_service(service_name)
    return APIResponse.success().to_dict()


@model_manage_bp.route('/task/progress', methods=['GET'])
@register_route(url_prefix + "/task/progress", "获取任务进度", "GET")
def get_task_progress():
    task_id = request.args.get("taskId")
    progress = rpc.manage_service.get_task_progress(task_id)
    return APIResponse.success_with_data(progress).flask_response()
