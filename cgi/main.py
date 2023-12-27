import time
import traceback
from datetime import datetime
from urllib.parse import urlparse

from flask import g, request

from cgi import app
from cgi.singleton import rpc, socketio, enforcer
from common.api_response import APIResponse
from common.error_code import ErrorCodeEnum
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
    if "Authorization" in request.headers:
        user = User()
        authorization = request.headers.get("Authorization")
        # print(f"auth = {authorization}")
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
        # print(f'casbin info: {sub} {obj} {act} -> {ok}')
        if not ok:
            return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.AUTH_ERROR).flask_response()


@app.after_request
def after_request(response):
    request_duration = time.time() - g.request_start_time

    log_data = {
        'user_id': g.user.id if g.user else -1,
        'method': request.method,
        'path': request.path,
        'status_code': response.status_code,
        'duration': request_duration,
        'response_json': response.get_json(),
        'time': datetime.now(),
    }
    if request.method != 'OPTIONS' and request.path not in ['/monitor/page', '/monitor/statistics]']:
        rpc.monitor_service.insert_request_log.call_async(log_data)
    # app.logger.info(log_data)

    return response


@app.errorhandler(Exception)
def handle_error(error):
    print(error)
    traceback.print_exc()
    return APIResponse(code=0, message=str(error)).flask_response()


if __name__ == '__main__':
    # print("start socketio")
    socketio.run(app, host='0.0.0.0', debug=False, port=8086)
