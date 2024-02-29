import multiprocessing
import time
from datetime import datetime
from urllib.parse import urlparse

import requests
from flask import g, request
from nameko.standalone.events import event_dispatcher

from cgi import app
from cgi.singleton import rpc, socketio, enforcer
from common import config
from common.api_response import APIResponse
from common.error_code import ErrorCodeEnum
from common.log import LOGGER
from common.util import decode_jwt
from model.user import User

rpc.init_app(app)


@app.route('/')
def hello_world():
    return 'Hello, World!'


@app.route('/heartbeat')
def heartbeat():
    rpc.user_service.hello()
    return 'keep-alive'


@app.before_request
def before_request():
    g.request_start_time = time.time()
    g.user = None

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

    if request.method != 'OPTIONS' and request.path not in ['/monitor/page', '/monitor/statistics']:
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
        with event_dispatcher(config.get_rpc_config()) as dispatcher:
            dispatcher("cgi", "insert_request_log", log_data)

    return response


@app.errorhandler(Exception)
def handle_error(error):
    LOGGER.error("error: %s", error, exc_info=True)
    return APIResponse(code=0, message=str(error)).flask_response()


def looping_heartbeat():
    LOGGER.info("start heartbeat")
    while True:
        time.sleep(600)
        url = "http://localhost:8086/heartbeat"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                LOGGER.info("Heartbeat OK")
            else:
                LOGGER.info("Heartbeat failed")
        except:
            pass


if __name__ == '__main__':
    LOGGER.info("start cgi")
    multiprocessing.Process(target=looping_heartbeat).start()
    socketio.run(app, host='0.0.0.0', debug=False, port=8086)
