import json

from cgi.singleton import rpc, socketio
from common.api_response import APIResponse
from common.error_code import ErrorCodeEnum


def recall(call_function, busy_check_function, json_data, max_call_times=10):
    call_cnt = 0
    output = call_function(json_data)
    while busy_check_function(output):
        output = call_function(json_data)
        call_cnt += 1
        if call_cnt >= max_call_times:
            return None
    return output


def async_call(call_function, busy_check_function, json_data, namespace, dynamicNamespace, max_call_times=10):
    output = recall(call_function, busy_check_function, json_data, max_call_times)
    if output is None:
        return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.SERVICE_BUSY_ERROR).flask_response()
    if type(output) == str:
        service_unique_id = json.loads(output)['unique_id']
    elif type(output) == dict:
        service_unique_id = output['unique_id']
    else:
        raise ValueError("output type error")
    dynamicNamespace.service_unique_id = service_unique_id
    socketio.on_namespace(dynamicNamespace)
    return APIResponse.success_with_data(namespace).flask_response()
