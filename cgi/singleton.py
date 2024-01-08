import casbin
from flask_nameko import FlaskPooledClusterRpcProxy
from flask_socketio import SocketIO

rpc = FlaskPooledClusterRpcProxy()
socketio = SocketIO()

enforcer = casbin.Enforcer("model.conf", "policy.csv")
enforcer.enable_auto_save(True)

permission_map = {}


def register_route(path, description, method):
    """一个简单的装饰器，用于注册路由到 route_map 中"""
    def decorator(func):
        if path in permission_map:
            raise ValueError(f"path: {path} has been used")
        permission_map[path] = {
            'description': description,
            'method': method,
        }
        return func

    return decorator
