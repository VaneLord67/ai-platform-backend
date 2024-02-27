import cgi
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

from flask import g, request

from cgi import app
from cgi.singleton import rpc, socketio, enforcer
from common.api_response import APIResponse
from common.error_code import ErrorCodeEnum
from common.log import LOGGER
from common.util import decode_jwt
from model.user import User

rpc.init_app(app)


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.before_request
def before_request():
    g.request_start_time = time.time()
    g.user = None

    rpc_current_time = datetime.now()
    rpc_diff_time = rpc_current_time - cgi.singleton.rpc_before_time
    if rpc_diff_time > timedelta(minutes=10):
        # 如果距离上一次重连超过10分钟，则进行一次重连，防止连接丢失，出现amqp异常
        try:
            cgi.singleton.rpc.hello()
        except:
            pass
        cgi.singleton.rpc_before_time = rpc_current_time

    if "Authorization" in request.headers:
        user = User()
        authorization = request.headers.get("Authorization")
        # LOGGER.info(f"auth = {authorization}")
        if authorization != "":
            jwt_dict = decode_jwt(authorization)
            if jwt_dict:
                user.username = jwt_dict['username']
                user.id = jwt_dict['id']
                g.user = user
    if request.path not in ['/user/login', '/user/register']:
        if g.user is None:
            return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.AUTH_ERROR).flask_response()
        sub = str(g.user.id)  # sub设计为user_id, casbin中的参数均为字符串类型

        url = request.path
        parsed_url = urlparse(url)
        # 获取URL的路径部分，不包括查询参数
        obj = parsed_url.netloc + parsed_url.path  # obj设计为HTTP URL PATH

        act = request.method  # act设计为HTTP API的method，例如GET POST DELETE等

        ok = enforcer.enforce(sub, obj, act)
        # LOGGER.info(f'casbin info: {sub} {obj} {act} -> {ok}')
        if not ok:
            return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.AUTH_ERROR).flask_response()


@app.after_request
def after_request(response):
    request_duration = time.time() - g.request_start_time

    status_code = None
    json_dict = response.get_json()
    if json_dict and 'code' in json_dict and json_dict['code'] != 1:
        # 如果服务端侧业务code不为1，则说明出错，那么令status_code为500，方便计算流量展示业务中的错误率
        status_code = 500

    log_data = {
        'user_id': g.user.id if g.user else -1,
        'method': request.method,
        'path': request.path,
        'status_code': status_code if status_code else response.status_code,
        'duration': request_duration,
        'response_json': response.get_json(),
        'time': datetime.now(),
    }
    if request.method != 'OPTIONS' and request.path not in ['/monitor/page', '/monitor/statistics']:
        rpc.monitor_service.insert_request_log.call_async(log_data)
    # app.logger.info(log_data)

    return response


@app.errorhandler(Exception)
def handle_error(error):
    LOGGER.error("error: %s", error, exc_info=True)
    return APIResponse(code=0, message=str(error)).flask_response()


if __name__ == '__main__':
    # LOGGER.info("start socketio")
    socketio.run(app, host='0.0.0.0', debug=False, port=8086)
