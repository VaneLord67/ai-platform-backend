from flask import Flask
from flask_cors import CORS

from cgi.detection import detection_bp, socketio
from cgi.manage import model_manage_bp
from cgi.monitor import monitor_bp
from cgi.object_storage import object_storage_bp
from cgi.user import user_bp
from common.config import config


def create_app():
    flaskApp = Flask(__name__)
    flaskApp.config['SECRET_KEY'] = config.get("jwt_secret")
    flaskApp.config.update(dict(
        NAMEKO_AMQP_URI=config.get("rabbitmq_url")
    ))
    flaskApp.register_blueprint(user_bp)
    flaskApp.register_blueprint(detection_bp)
    flaskApp.register_blueprint(model_manage_bp)
    flaskApp.register_blueprint(object_storage_bp)
    flaskApp.register_blueprint(monitor_bp)

    socketio.init_app(flaskApp, cors_allowed_origins='*')

    CORS(flaskApp)
    return flaskApp


app = create_app()
