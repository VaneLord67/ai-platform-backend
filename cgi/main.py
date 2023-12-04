from . import app
from .singleton import rpc

rpc.init_app(app)


@app.route('/')
def hello_world():
    return 'Hello, World!'
