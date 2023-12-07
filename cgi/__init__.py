from flask import Flask
from flask_cors import CORS

from cgi.detection import detection_bp
from cgi.manage import model_manage_bp
from cgi.user import user_bp
from common.const import AMQP_URI


def create_app():
    flaskApp = Flask(__name__)
    CORS(flaskApp)
    flaskApp.config.update(dict(
        NAMEKO_AMQP_URI=AMQP_URI
    ))
    flaskApp.register_blueprint(user_bp)
    flaskApp.register_blueprint(detection_bp)
    flaskApp.register_blueprint(model_manage_bp)
    return flaskApp


app = create_app()
