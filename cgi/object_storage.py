from flask import request, Blueprint

from common.api_response import APIResponse
from .singleton import rpc, register_route

url_prefix = "/object_storage"
object_storage_bp = Blueprint('object_storage', __name__, url_prefix=url_prefix)


@object_storage_bp.route('/presigned_url', methods=['GET'])
@register_route(url_prefix + "/presigned_url", "获取对象存储预签名URL", "GET")
def get_presigned_url():
    object_name = request.args.get("objectName")
    presigned_url = rpc.object_storage_service.get_presigned_url(object_name)
    return APIResponse.success_with_data(presigned_url).to_dict()


@object_storage_bp.route('/url', methods=['GET'])
@register_route(url_prefix + "/url", "获取对象存储URL", "GET")
def get_url():
    object_name = request.args.get("objectName")
    url = rpc.object_storage_service.get_object_url(object_name)
    return APIResponse.success_with_data(url).to_dict()
