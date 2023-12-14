from flask import request, Blueprint

from common.api_response import APIResponse
from .singleton import rpc

object_storage_bp = Blueprint('object_storage', __name__, url_prefix='/object_storage')


@object_storage_bp.route('/presigned_url', methods=['GET'])
def get_presigned_url():
    object_name = request.args.get("objectName")
    presigned_url = rpc.object_storage_service.get_presigned_url(object_name)
    return APIResponse.success_with_data(presigned_url).to_dict()


@object_storage_bp.route('/url', methods=['GET'])
def get_url():
    object_name = request.args.get("objectName")
    url = rpc.object_storage_service.get_object_url(object_name)
    return APIResponse.success_with_data(url).to_dict()

