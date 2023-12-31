import base64
import uuid
from datetime import timedelta
from typing import Union

from flask_socketio import Namespace

from cgi.singleton import rpc
from common.log import LOGGER
from common.util import get_log_from_redis, create_redis_client
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
        # self.stop_signal_key: str = "stop"
        # self.queue_name: str = "my_queue"
        self.service_unique_id = service_unique_id
        self.log_key = unique_id + "_log"
        self.video_progress_key: str = unique_id + "_video_progress"
        self.redis_client = create_redis_client()

    def set_json_data(self, json_data):
        if self.source == CAMERA_TYPE:
            json_data['stopSignalKey'] = self.stop_signal_key
            json_data['queueName'] = self.queue_name
            json_data['logKey'] = self.log_key
        elif self.source == VIDEO_URL_TYPE:
            json_data['stopSignalKey'] = self.stop_signal_key
            json_data['logKey'] = self.log_key
            json_data['videoProgressKey'] = self.video_progress_key
            json_data['taskId'] = self.unique_id
        return json_data

    def on_connect(self):
        LOGGER.info(f'Client connected to namespace: {self.namespace}, stop_key = {self.stop_signal_key}')

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

    def on_camera_retrieve(self, data):
        client = self.redis_client
        logs = get_log_from_redis(client, self.log_key)
        if logs and len(logs) > 0:
            # LOGGER.info("logs:", logs)
            self.emit(event='camera_log', namespace=self.namespace, data=logs)
        result = client.blpop([self.queue_name], timeout=1)  # timeout for seconds
        queue_data = result[1] if result else None
        if queue_data is None:
            self.emit(event='camera_data', namespace=self.namespace, data='')
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
        LOGGER.info("stop camera...")
        pipeline = self.redis_client.pipeline()
        pipeline.set(self.stop_signal_key, "1", ex=timedelta(seconds=60))
        pipeline.delete(self.queue_name)
        pipeline.delete(self.log_key)
        pipeline.expire(self.queue_name, time=timedelta(seconds=60))
        pipeline.expire(self.log_key, time=timedelta(seconds=60))
        pipeline.execute()
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
            self.on_stop_camera(data=None)
        self.socketio.server.namespace_handlers.pop(self.namespace)

    @staticmethod
    def init_parameter(json_data):
        source = json_data['supportInput']['type']
        unique_id = str(uuid.uuid4())
        namespace = '/' + unique_id
        return source, namespace, unique_id
