import uuid
from datetime import timedelta

from nameko.rpc import rpc

from common.util import get_filename_and_ext
from microservice.minio_storage import MinioStorage


class ObjectStorageService:
    name = "object_storage_service"
    minio_storage = MinioStorage()

    def __init__(self):
        pass

    @rpc
    def get_presigned_url(self, object_name):
        client = self.minio_storage.client
        bucket_name = self.minio_storage.bucket_name
        url = client.presigned_put_object(bucket_name, object_name, expires=timedelta(days=1))
        return url

    @rpc
    def get_object_url(self, object_name):
        client = self.minio_storage.client
        bucket_name = self.minio_storage.bucket_name
        url = client.presigned_get_object(bucket_name, object_name, expires=timedelta(hours=24))
        return url

    @rpc
    def upload_object(self, object_path):
        client = self.minio_storage.client
        bucket_name = self.minio_storage.bucket_name
        file_name, file_ext = get_filename_and_ext(object_path)
        unique_id = str(uuid.uuid4())
        new_file_name = f"{file_name}_{unique_id}{file_ext}"
        content_type = "application/octet-stream"
        if 'mp4' in file_ext:
            content_type = "video/mp4"
        result = client.fput_object(
            bucket_name, new_file_name, object_path, content_type=content_type
        )
        object_name = result.object_name
        url = self.get_object_url(object_name)
        return url


