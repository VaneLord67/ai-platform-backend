import time
import uuid
from datetime import timedelta
from typing import Union

from flask import request
from flask_socketio import Namespace

from cgi.singleton import rpc
from common.log import LOGGER
from common.util import get_log_from_redis, create_redis_client
from microservice.mqtt_storage import MQTTStorage
from model.support_input import VIDEO_URL_TYPE, CAMERA_TYPE


class DynamicNamespace(Namespace):
    """
    这是用于Socket-IO库的辅助类，服务器会给每一个前端创建单独的namespace，在namespace中进行实时数据的传输
    """

    def __init__(self, namespace, unique_id, service_unique_id=None, service_name=None, source=None):
        super().__init__(namespace)
        self.source: str = source if source else VIDEO_URL_TYPE
        self.service_name: str = service_name
        self.unique_id: str = unique_id
        self.stop_signal_key: str = unique_id + "_stop"
        self.queue_name: str = unique_id + "_queue_name"
        self.service_unique_id = service_unique_id
        self.log_key = unique_id + "_log"
        self.video_progress_key: str = unique_id + "_video_progress"
        self.redis_client = create_redis_client()
        self.mqtt_storage = MQTTStorage()
        self.consumer_id = None
        self.producer_id = None

    def set_json_data(self, json_data):
        json_data['taskId'] = self.unique_id
        json_data['namespace'] = self.namespace
        if self.source == CAMERA_TYPE:
            json_data['stopSignalKey'] = self.stop_signal_key
            json_data['queueName'] = self.queue_name
            json_data['logKey'] = self.log_key
        elif self.source == VIDEO_URL_TYPE:
            json_data['stopSignalKey'] = self.stop_signal_key
            json_data['logKey'] = self.log_key
            json_data['videoProgressKey'] = self.video_progress_key
        return json_data

    def on_connect(self):
        LOGGER.info(f'Client connected to namespace: {self.namespace}, stop_key = {self.stop_signal_key}')

    def on_post_consumer_id(self):
        self.consumer_id = request.sid
        LOGGER.info(f'sid received on post_consumer_id: {self.consumer_id}')

    def on_post_producer_id(self):
        self.producer_id = request.sid
        LOGGER.info(f'sid received on post_producer_id: {self.producer_id}')

    def on_progress_retrieve(self, data):
        client = self.redis_client
        logs = get_log_from_redis(client, self.log_key)
        if logs and len(logs) > 0:
            self.emit(event='video_log', namespace=self.namespace, data=logs)
        task_done = client.hlen(self.unique_id) == 2
        if task_done:
            video_url = client.hget(name=self.unique_id, key="video_url").decode('utf-8')
            json_url = client.hget(name=self.unique_id, key="json_url").decode('utf-8')
            self.emit(event='video_task_done', namespace=self.namespace, data=[video_url, json_url])
            LOGGER.info(f'emit video_task_done event, task_id: {self.unique_id}')
        else:
            progress: Union[bytes, None] = client.get(self.video_progress_key)
            if progress:
                self.emit(event='progress_data', namespace=self.namespace, data=progress.decode('utf-8'))
            else:
                self.emit(event='progress_data', namespace=self.namespace, data='0.00')

    def on_log(self, data):
        self.emit(event='log', data=data, room=self.consumer_id, namespace=self.namespace)

    def on_camera_retrieve(self):
        self.emit('camera_retrieve', room=self.producer_id, namespace=self.namespace)

    def on_camera_data(self, data):
        self.emit(event='camera_data', data=data, room=self.consumer_id, namespace=self.namespace)

    def on_time_sync_request(self):
        self.emit(event='time_sync', data=int(time.time() * 1000), room=self.consumer_id, namespace=self.namespace)

    def on_stop_camera(self):
        LOGGER.info(f"{self.namespace} stop camera...")
        self.emit(event='stop_camera', room=self.producer_id, namespace=self.namespace)
        rpc.manage_service.change_state_to_ready(self.service_name, self.service_unique_id)

    def clear_video_resource(self):
        pipeline = self.redis_client.pipeline()
        pipeline.set(self.stop_signal_key, "1", ex=timedelta(seconds=60))
        pipeline.delete(self.log_key)
        pipeline.expire(self.log_key, time=timedelta(seconds=60))
        pipeline.delete(self.video_progress_key)
        pipeline.expire(self.video_progress_key, time=timedelta(seconds=60))
        pipeline.execute()
        rpc.manage_service.change_state_to_ready(self.service_name, self.service_unique_id)

    def on_disconnect(self):
        LOGGER.info(f'Client disconnected from namespace: {self.namespace}')
        if self.source == VIDEO_URL_TYPE:
            self.clear_video_resource()
        elif self.source == CAMERA_TYPE:
            self.on_stop_camera()
        self.socketio.server.namespace_handlers.pop(self.namespace)

    @staticmethod
    def init_parameter(json_data):
        source = json_data['supportInput']['type']
        unique_id = str(uuid.uuid4())
        namespace = '/' + unique_id
        return source, namespace, unique_id
