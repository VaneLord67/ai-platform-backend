import base64
from datetime import timedelta
from typing import Union

import redis
from flask_socketio import Namespace

from ais.opencv_track import set_roi_to_redis
from cgi.singleton import rpc
from common.config import config
from microservice.track import TrackService
from model.track_result import TrackResult


class DynamicNamespace(Namespace):

    def __init__(self, namespace, unique_id, service_unique_id=None, service_name=None):
        super().__init__(namespace)
        self.service_name: str = service_name
        self.unique_id: str = unique_id
        self.stop_signal_key: str = unique_id + "_stop"
        self.queue_name: str = unique_id + "_queue_name"
        # self.stop_signal_key: str = "stop"
        # self.queue_name: str = "my_queue"
        self.service_unique_id = service_unique_id
        self.redis_client: Union[redis.StrictRedis, None] = redis.StrictRedis.from_url(config.get("redis_url"))

        if self.service_name == TrackService.name:
            self.roi_key = unique_id + "_roi"

    def on_connect(self):
        print(f'Client connected to namespace: {self.namespace}, stop_key = {self.stop_signal_key}')

    def on_roi_event(self, roi_data):
        roi: TrackResult = TrackResult().from_json(roi_data)
        set_roi_to_redis(roi, self.roi_key, self.redis_client)

    def on_camera_retrieve(self, data):
        client = self.redis_client
        _, queue_data = client.blpop([self.queue_name])
        if queue_data and queue_data != b'stop':
            self.frame_with_json_handler(queue_data)

    def frame_with_json_handler(self, queue_data):
        if queue_data[:len(b'{')] == b'{' or queue_data[:len(b'[')] == b'[':
            self.emit(event='camera_data', namespace=self.namespace, data=queue_data.decode('utf-8'))
        else:
            self.emit_jpg_text(queue_data)

    def emit_jpg_text(self, queue_data):
        jpg_as_text = base64.b64encode(queue_data).decode('utf-8')
        self.emit(event='camera_data', namespace=self.namespace, data=jpg_as_text)

    def on_stop_camera(self, data):
        print("stop camera...")
        self.redis_client.set(self.stop_signal_key, "1", ex=timedelta(seconds=60))
        self.redis_client.delete(self.queue_name)
        self.redis_client.expire(self.queue_name, time=timedelta(seconds=60))
        rpc.manage_service.change_state_to_ready(self.service_name, self.service_unique_id)

    def on_disconnect(self):
        print(f'Client disconnected from namespace: {self.namespace}')
        self.on_stop_camera(data=None)
        self.socketio.server.namespace_handlers.pop(self.namespace)
