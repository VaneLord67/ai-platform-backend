from datetime import datetime

import casbin
from flask_nameko import FlaskPooledClusterRpcProxy
from flask_socketio import SocketIO

rpc = FlaskPooledClusterRpcProxy()
rpc_before_time = datetime.now()
socketio = SocketIO()

enforcer = casbin.Enforcer("model.conf", "policy.csv")
enforcer.enable_auto_save(True)

permission_map = {}


def register_route(path, description, method):
    """一个简单的装饰器，用于注册路由到 route_map 中"""
    def decorator(func):
        if path in permission_map and method in permission_map[path]:
            raise ValueError(f"path: {path} with method {method} has been used")
        if path not in permission_map:
            permission_map[path] = {}
        permission_map[path][method] = {
            'description': description,
        }
        return func

    return decorator
