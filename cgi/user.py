from flask import request, Blueprint

from common.api_response import APIResponse
from common.error_code import ErrorCodeEnum
from model.permission import Permission
from model.user import User
from .singleton import rpc, register_route, permission_map, enforcer

url_prefix = '/user'
user_bp = Blueprint('user', __name__, url_prefix=url_prefix)


@user_bp.route('/login', methods=['POST'])
def login():
    json_data = request.get_json()
    user = User().from_dict(json_data)
    jwt = rpc.user_service.login(user)
    response = APIResponse.success_with_data(jwt) if jwt != "" else APIResponse.fail()
    return response.to_dict()


@user_bp.route('/register', methods=['POST'])
def register():
    json_data = request.get_json()
    user = User().from_dict(json_data)
    jwt = rpc.user_service.register(user)
    enforcer.add_role_for_user(str(user.id), 'guest')
    enforcer.save_policy()
    response = APIResponse.success_with_data(jwt) if jwt != "" else APIResponse.fail()
    return response.to_dict()


@user_bp.route('/page', methods=['GET'])
@register_route(url_prefix + '/page', "获取用户列表", 'GET')
def get_user_page():
    page_size = request.args.get('pageSize', default=5, type=int)
    page_num = request.args.get('pageNum', default=1, type=int)
    total_num = rpc.user_service.get_user_total_num()
    total_page = (total_num + page_size - 1) // page_size
    user_json_strs = rpc.user_service.get_user_page(page_num, page_size)
    users = []
    for user_json_str in user_json_strs:
        users.append(User().from_json(user_json_str))
    payload = {
        'total_page': total_page,
        'total_num': total_num,
        'data': users
    }
    return APIResponse.success_with_data(payload).flask_response()


@user_bp.route('/', methods=['PUT'])
@register_route(url_prefix, "编辑用户", "PUT")
def update_user():
    json_dict = request.get_json()
    new_user = User().from_dict(json_dict)
    old_user_json = rpc.user_service.get_user_by_id(new_user.id)
    if old_user_json:
        rpc.user_service.update_user_by_id(new_user.id, new_user.username, new_user.role)
        enforcer.delete_roles_for_user(str(new_user.id))
        enforcer.add_role_for_user(str(new_user.id), new_user.role)
        enforcer.save_policy()
        return APIResponse.success().flask_response()
    else:
        return APIResponse.fail().flask_response()


@user_bp.route('/', methods=['DELETE'])
@register_route(url_prefix, "删除用户", "DELETE")
def delete_user():
    user_id = request.args.get('userId', type=int)
    if user_id is None:
        return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.ARGUMENT_ERROR)
    rpc.user_service.delete_user(user_id)
    return APIResponse.success().flask_response()


@user_bp.route('/permission', methods=['GET'])
@register_route(url_prefix + '/permission', "获取权限列表", "GET")
def get_permissions():
    permissions = []
    for path, methods in permission_map.items():
        for method, other in methods.items():
            permissions.append(Permission(route=path, act=method, description=other['description']))
    return APIResponse.success_with_data(permissions).flask_response()


@user_bp.route("/permission/role", methods=['GET'])
@register_route(url_prefix + "/permission/role", "获取角色允许的权限列表", "GET")
def get_role_permissions():
    role = request.args.get(key='role', type=str)
    casbin_permissions = enforcer.get_permissions_for_user(role)
    permissions = []
    for casbin_permission in casbin_permissions:
        if casbin_permission[1] in permission_map:
            description = permission_map[casbin_permission[1]][casbin_permission[2]]['description']
            permissions.append(Permission(role=casbin_permission[0], route=casbin_permission[1],
                                          act=casbin_permission[2], description=description))
    return APIResponse.success_with_data(permissions).flask_response()


@user_bp.route('/role', methods=['GET'])
@register_route(url_prefix + "/role", "获取角色列表", "GET")
def get_roles():
    roles = enforcer.get_all_roles()
    return APIResponse.success_with_data(roles).flask_response()


@user_bp.route('/permission/role', methods=['PUT'])
@register_route(url_prefix + "/permission/role", "修改角色允许的权限列表", "PUT")
def update_role_permissions():
    json_dict = request.get_json()
    role = json_dict['role']
    permission_jsons = json_dict['permissions']
    permissions = []
    for permission_json in permission_jsons:
        permissions.append(Permission().from_dict(permission_json))
    enforcer.delete_permissions_for_user(role)
    for permission in permissions:
        if permission.route in permission_map:
            enforcer.add_permission_for_user(role, permission.route, permission.act)
    enforcer.save_policy()
    return APIResponse.success().flask_response()
