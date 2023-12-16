import time
from datetime import datetime

from flask import g, request

from common.util import decode_jwt, connect_to_database
from model.user import User
from . import app
from .singleton import rpc

rpc.init_app(app)

conn = connect_to_database()


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
    if request.method != 'OPTIONS' and request.path != '/monitor/page':
        rpc.monitor_service.insertRequestLog.call_async(log_data)
    # app.logger.info(log_data)

    return response
