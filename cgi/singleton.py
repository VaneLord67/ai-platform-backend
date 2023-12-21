from flask_nameko import FlaskPooledClusterRpcProxy
from flask_socketio import SocketIO

rpc = FlaskPooledClusterRpcProxy()
socketio = SocketIO()
