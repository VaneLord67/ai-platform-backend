from flask import request, Blueprint

from common.api_response import APIResponse
from model.request_log import RequestLog
from model.statistics import Statistics
from .singleton import rpc, register_route

url_prefix = "/monitor"
monitor_bp = Blueprint('monitor', __name__, url_prefix=url_prefix)


@monitor_bp.route('/page', methods=['GET'])
@register_route(url_prefix + "/page", "获取请求日志", "GET")
def get_monitor_data_page():
    page_size = request.args.get('pageSize', default=5, type=int)
    page_num = request.args.get('pageNum', default=1, type=int)
    username = request.args.get('username', default="", type=str)
    service_name = request.args.get('serviceName', default="", type=str)
    start_time = request.args.get('startTime', default=0, type=int)
    end_time = request.args.get('endTime', default=0, type=int)
    input_mode = request.args.get('inputMode', default="", type=str)

    total_num = rpc.monitor_service.get_total_num(username, service_name, start_time, end_time, input_mode)
    total_page = (total_num + page_size - 1) // page_size
    request_log_json_strs = rpc.monitor_service.get_monitor_data_list(page_num, page_size,
                                                                      username, service_name,
                                                                      start_time, end_time, input_mode)
    request_logs = []
    for request_log_json_str in request_log_json_strs:
        request_logs.append(RequestLog().from_json(request_log_json_str))
    payload = {
        'total_page': total_page,
        'total_num': total_num,
        'data': request_logs
    }
    return APIResponse.success_with_data(payload).flask_response()


@monitor_bp.route('/load', methods=['GET'])
@register_route(url_prefix + "/load", "获取硬件负载", "GET")
def get_load():
    load = rpc.manage_service.get_load()
    return APIResponse.success_with_data(load).flask_response()


@monitor_bp.route('/statistics', methods=['GET'])
@register_route(url_prefix + "/statistics", "获取流量统计信息", "GET")
def get_statistics():
    statistics = rpc.monitor_service.get_statistics()

    statistics_for_hour = []
    statistics_for_day = []
    for statistic_json_str in statistics['statistics_for_hour']:
        statistic = Statistics().from_json(statistic_json_str)
        statistics_for_hour.append(statistic)
    for statistic_json_str in statistics['statistics_for_day']:
        statistic = Statistics().from_json(statistic_json_str)
        statistics_for_day.append(statistic)
    r = {
        'statistics_for_day': statistics_for_day,
        'statistics_for_hour': statistics_for_hour
    }
    return APIResponse.success_with_data(r).flask_response()
