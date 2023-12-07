from datetime import timedelta

from nameko.rpc import rpc

from common.config import config
from common.model import User
from common.util import generate_jwt
from microservice.minio_storage import MinioStorage


class ObjectStorageService:
    name = "object_storage_service"
    minio_storage = MinioStorage()

    def __init__(self):
        pass

    @rpc
    def get_presigned_url(self, object_name):
        client = self.minio_storage.client
        bucket_name = config.get("bucket_name")
        url = client.presigned_put_object(bucket_name, object_name, expires=timedelta(days=1))
        return url
