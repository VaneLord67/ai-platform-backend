import multiprocessing
import os
import threading
import time
import uuid
from abc import ABC
from datetime import timedelta
from typing import List, Union

from nameko.events import event_handler, BROADCAST
from nameko.rpc import RpcProxy, rpc
from nameko.standalone.rpc import ClusterRpcProxy

from common import config
from common.util import download_file, clear_image_temp_resource, create_redis_client
from microservice.manage import ManageService
from microservice.object_storage import ObjectStorageService
from microservice.redis_storage import RedisStorage
from model.hyperparameter import Hyperparameter
from model.service_info import ServiceInfo, ServiceReadyState, ServiceRunningState
from model.support_input import SupportInput, SINGLE_PICTURE_URL_TYPE, MULTIPLE_PICTURE_URL_TYPE, VIDEO_URL_TYPE, \
    CAMERA_TYPE


class AIBaseService(ABC):
    name = "ai_base_service"

    unique_id = str(uuid.uuid4())
    service_info = ServiceInfo()
    state_lock = threading.Lock()

    redis_storage = RedisStorage()

    object_storage_service = RpcProxy(ObjectStorageService.name)

    def __init__(self):
        self.hyperparameters: Union[List[Hyperparameter], None] = None
        self.args: Union[dict, None] = None
        self.support_input: Union[SupportInput, None] = None

    @rpc
    def foo(self):
        multiprocessing.Process(target=self.bar, daemon=True).start()
        return "foo done"

    @staticmethod
    def bar():
        print("hello!")

    @event_handler(ManageService.name, name + "state_report", handler_type=BROADCAST, reliable_delivery=False)
    def state_report(self, payload):
        redis_list_key = payload
        self.state_lock.acquire()
        try:
            state_string = self.service_info.__str__()
            self.redis_storage.client.rpush(redis_list_key, state_string)
        finally:
            self.state_lock.release()

    @event_handler(ManageService.name, name + "close_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_event_handler(self, payload):
        print("receive close event")
        raise KeyboardInterrupt

    @event_handler(ManageService.name, name + "close_one_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_one_event_handler(self, payload):
        print("receive close one event")
        close_unique_id = payload
        print(f"close_unique_id = {close_unique_id}")
        lock_ok = self.redis_storage.client.set(close_unique_id, "locked", ex=timedelta(minutes=1), nx=True)
        if lock_ok:
            print("get close lock, raise KeyboardInterrupt...")
            raise KeyboardInterrupt
        else:
            print("close lock failed, continue running...")

    @event_handler(ManageService.name, name + "state_change", handler_type=BROADCAST, reliable_delivery=False)
    def state_to_ready_handler(self, payload):
        if self.unique_id == payload:
            self.state_lock.acquire()
            self.service_info.state = ServiceReadyState
            self.state_lock.release()

    @rpc
    def call(self, args: dict):
        self.state_lock.acquire()
        supportInput = SupportInput().from_dict(args['supportInput'])
        self.support_input = supportInput
        self.args = args
        output = self.call_init()
        try:
            if output['busy']:
                return output
            hyperparameters = AIBaseService.parse_hyperparameters(args)
            self.hyperparameters = hyperparameters
            if supportInput.type == SINGLE_PICTURE_URL_TYPE:
                img_url = self.support_input.value
                result = self.handle_single_image(img_url)
                output.update(result)
                return output
            elif supportInput.type == MULTIPLE_PICTURE_URL_TYPE:
                img_urls = supportInput.value
                merged_result = {}
                for img_url in img_urls:
                    result = self.handle_single_image(img_url)
                    AIBaseService.merge_single_result(merged_result, result)
                output.update(merged_result)
                return output
            elif supportInput.type == VIDEO_URL_TYPE:
                self.handle_video()
                return output
            elif supportInput.type == CAMERA_TYPE:
                self.handle_camera()
                return output
            else:
                raise NotImplementedError("input type not support")
        except Exception as e:
            self.service_info.state = ServiceReadyState
            raise e
        finally:
            if supportInput.type not in [CAMERA_TYPE, VIDEO_URL_TYPE]:
                self.service_info.state = ServiceReadyState
            self.state_lock.release()

    def handle_single_image(self, img_url) -> dict:
        """
        return type like this:

        return {
            'frames': [],
            'log_strs': [],
            ...
        }
        """
        img_name, img_path = download_file(img_url)
        unique_id = str(uuid.uuid4())
        output_path = f"temp/{img_name}_{unique_id}/"
        try:
            os.makedirs(output_path, exist_ok=True)
            print(f"Folder '{output_path}' created successfully.")
            return self.single_image_cpp_call(img_path, output_path, self.hyperparameters)
        finally:
            clear_image_temp_resource(img_path, output_path)

    @staticmethod
    def single_image_cpp_call(img_path, output_path, hyperparameters):
        raise NotImplementedError("please implement single_image_cpp_call")

    def handle_video(self):
        video_url = self.support_input.value
        video_progress_key = self.args['videoProgressKey']

        video_name, video_path = download_file(video_url)
        if 'taskId' not in self.args:
            raise ValueError("task id not found!")
        task_id = self.args['taskId']
        output_video_path = f"temp/output_{video_name}"
        output_jsonl_path = f"temp/output_{task_id}.jsonl"

        multiprocessing.Process(target=self.video_cpp_call, daemon=True,
                                args=[video_path, output_video_path, output_jsonl_path, video_progress_key,
                                      self.hyperparameters, task_id, self.unique_id]).start()

    @staticmethod
    def video_cpp_call(video_path, output_video_path, output_jsonl_path, video_progress_key,
                       hyperparameters, task_id, unique_id):
        raise NotImplementedError("please implement video_cpp_call")

    def handle_camera(self):
        camera_id = self.support_input.value
        stop_signal_key = self.args['stopSignalKey']
        camera_data_queue_name = self.args['queueName']
        log_key = self.args['logKey']
        multiprocessing.Process(target=self.camera_cpp_call, daemon=True,
                                args=[camera_id, self.hyperparameters, stop_signal_key,
                                      camera_data_queue_name, log_key]).start()

    @staticmethod
    def camera_cpp_call(camera_id, hyperparameters, stop_signal_key,
                        camera_data_queue_name, log_key):
        raise NotImplementedError("please implement camera_cpp_call")

    def call_init(self):
        output = {
            'busy': False,
            'unique_id': self.unique_id,
        }
        if 'taskId' in self.args:
            output['task_id'] = self.args['taskId']
        if self.service_info.state != ServiceReadyState:
            output['busy'] = True
            return output
        self.service_info.task_start_time = int(time.time() * 1000)
        self.service_info.task_type = self.support_input.type
        self.service_info.state = ServiceRunningState
        return output

    @staticmethod
    def parse_hyperparameters(args):
        hyperparameters = []
        if 'hyperparameters' in args:
            hps = args['hyperparameters']
            for hp in hps:
                hyperparameters.append(Hyperparameter().from_dict(hp))
        return hyperparameters

    @staticmethod
    def merge_single_result(merged_result, single_result):
        for key, value in single_result.items():
            # 如果当前键已存在于合并后的字典中，就将其列表扩展
            if key in merged_result:
                merged_result[key].extend(value)
            # 如果当前键不存在于合并后的字典中，就将其添加到合并后的字典中
            else:
                merged_result[key] = value[:]

    @staticmethod
    def after_video_call(video_output_path, video_output_json_path, task_id, service_name, service_unique_id):
        with ClusterRpcProxy(config.get_rpc_config()) as cluster_rpc:
            video_url = cluster_rpc.object_storage_service.upload_object(video_output_path)
            json_url = cluster_rpc.object_storage_service.upload_object(video_output_json_path)
            client = create_redis_client()
            mapping = {
                "video_url": video_url,
                "json_url": json_url,
            }
            client.hset(name=task_id, mapping=mapping)
            client.expire(name=task_id, time=timedelta(hours=24))
            cluster_rpc.manage_service.change_state_to_ready(service_name, service_unique_id)
            print(f"video task done, task_id:{task_id}")