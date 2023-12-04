from flask import request, Blueprint

from .singleton import rpc
from common.model import User
from common.util import APIResponse
user_bp = Blueprint('user', __name__, url_prefix='/user')


@user_bp.route('/login', methods=['POST'])
def login():
    json_data = request.get_json()
    user = User.from_json(json_data)
    jwt = rpc.user_service.login(user)
    response = APIResponse.success_with_data(jwt) if jwt != "" else APIResponse.fail()
    return response.to_dict()


@user_bp.route('/register', methods=['POST'])
def register():
    json_data = request.get_json()
    user = User.from_json(json_data)
    jwt = rpc.user_service.register(user)
    response = APIResponse.success_with_data(jwt) if jwt != "" else APIResponse.fail()
    return response.to_dict()
