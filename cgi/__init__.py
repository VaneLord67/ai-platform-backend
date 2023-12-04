from flask import Flask

from cgi.user import user_bp


def create_app():
    flaskApp = Flask(__name__)
    flaskApp.config.update(dict(
        NAMEKO_AMQP_URI='pyamqp://guest:guest@localhost'
    ))
    flaskApp.register_blueprint(user_bp)
    return flaskApp


app = create_app()
