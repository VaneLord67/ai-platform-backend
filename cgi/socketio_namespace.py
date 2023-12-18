import base64
from datetime import timedelta
from typing import Union

import redis
from flask_socketio import Namespace

from cgi.singleton import rpc
from common.config import config
from microservice.detection import DetectionService


class DynamicNamespace(Namespace):

    def __init__(self, namespace, unique_id, service_unique_id=None):
        super().__init__(namespace)
        self.unique_id: str = unique_id
        self.stop_signal_key: str = unique_id + "_stop"
        # self.stop_signal_key: str = "stop"
        self.queue_name: str = unique_id + "_queue_name"
        # self.queue_name: str = "my_queue"
        self.service_unique_id = service_unique_id
        self.redis_client: Union[redis.StrictRedis, None] = redis.StrictRedis.from_url(config.get("redis_url"))

    def on_connect(self):
        print(f'Client connected to namespace: {self.namespace}, stop_key = {self.stop_signal_key}')

    def on_camera_retrieve(self, data):
        client = self.redis_client
        _, queue_data = client.blpop([self.queue_name])
        if queue_data and queue_data != b'stop':
            if queue_data[:len(b'[')] == b'[':
                _, queue_data = client.blpop([self.queue_name])
            jpg_as_text = base64.b64encode(queue_data).decode('utf-8')
            self.emit(event='camera_data', namespace=self.namespace, data=jpg_as_text)

    def on_stop_camera(self, data):
        print("stop camera...")
        self.redis_client.set(self.stop_signal_key, "1", ex=timedelta(hours=1))
        # rpc.detection_service.stopCamera(self.stop_signal_key)
        self.redis_client.delete(self.queue_name)
        rpc.manage_service.change_state_to_ready(DetectionService.name, self.service_unique_id)

    def on_disconnect(self):
        print(f'Client disconnected from namespace: {self.namespace}')
        self.on_stop_camera(data=None)
        self.socketio.server.namespace_handlers.pop(self.namespace)
