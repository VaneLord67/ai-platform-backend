from flask import request, Blueprint

from common.api_response import APIResponse
from model.request_log import RequestLog
from model.statistics import Statistics
from .singleton import rpc

monitor_bp = Blueprint('monitor', __name__, url_prefix='/monitor')


@monitor_bp.route('/page', methods=['GET'])
def get_monitor_data_page():
    page_size = request.args.get('pageSize', default=5, type=int)
    page_num = request.args.get('pageNum', default=1, type=int)
    total_num = rpc.monitor_service.get_total_num()
    total_page = (total_num + page_size - 1) // page_size
    request_log_json_strs = rpc.monitor_service.get_monitor_data_list(page_num, page_size)
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
def get_load():
    load = rpc.manage_service.get_load()
    return APIResponse.success_with_data(load).flask_response()


@monitor_bp.route('/statistics', methods=['GET'])
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
