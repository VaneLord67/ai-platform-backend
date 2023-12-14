from typing import Union

from minio import Minio
from nameko.extensions import DependencyProvider

from common.config import config


class MinioStorageWrapper:

    def __init__(self, client):
        self.client = client
        self.bucket_name = config.config.get("bucket_name")


class MinioStorage(DependencyProvider):

    def __init__(self):
        self.client: Union[Minio, None] = None
        self.bucket_name = config.config.get("bucket_name")

    def setup(self):
        self.client = Minio(
            config.get("minio_url"),
            access_key=config.get("minio_access_key"),
            secret_key=config.get("minio_secret_key"),
            secure=False  # 如果Minio服务器不启用SSL，请将此值设置为False
        )

    def get_dependency(self, worker_ctx):
        return MinioStorageWrapper(self.client)
