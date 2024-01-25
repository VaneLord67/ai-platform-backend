import json
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
from common.log import LOGGER
from common.util import download_file, clear_image_temp_resource, create_redis_client
from microservice.manage import ManageService
from microservice.mqtt_storage import MQTTStorage
from microservice.object_storage import ObjectStorageService
from microservice.redis_storage import RedisStorage
from model.hyperparameter import Hyperparameter
from model.service_info import ServiceInfo, ServiceReadyState, ServiceRunningState
from model.support_input import SupportInput, SINGLE_PICTURE_URL_TYPE, MULTIPLE_PICTURE_URL_TYPE, VIDEO_URL_TYPE, \
    CAMERA_TYPE


class AIBaseService(ABC):
    """
    AIBaseService抽象基类，使用模板方法模式设计，用于复用AI微服务的重复代码

    衍生子类需要声明父类的event_handler函数并调用父类处理函数，如果不声明则不会触发事件
    衍生子类需要实现cpp_call簇的函数，函数内调用pybind绑定的c++接口，如果不实现会在运行期报错

    由于部分cpp_call是使用的多进程进行调用，nameko中的self不能在进程之间进行传递，
    所以声明为类函数，无法在所谓编译期进行子类实现接口的检查（如果你有更好的方法，可以将其改进）
    """
    name = "ai_base_service"

    unique_id = str(uuid.uuid4())
    service_info = ServiceInfo()
    state_lock = threading.Lock()

    redis_storage = RedisStorage()
    mqtt_storage = MQTTStorage()

    object_storage_service = RpcProxy(ObjectStorageService.name)

    def __init__(self):
        self.hyperparameters: Union[List[Hyperparameter], None] = None
        self.args: Union[dict, None] = None
        self.support_input: Union[SupportInput, None] = None

    @event_handler(ManageService.name, name + "state_report", handler_type=BROADCAST, reliable_delivery=False)
    def state_report(self, payload):
        """
        ManageService会发布state_report事件，AI微服务监听到事件后使用redis来进行服务信息的上报，
        后续ManageService会从redis中收集服务信息
        """
        redis_list_key = payload
        self.state_lock.acquire()
        try:
            state_string = self.service_info.__str__()
            self.redis_storage.client.rpush(redis_list_key, state_string)
        finally:
            self.state_lock.release()

    @event_handler(ManageService.name, name + "close_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_event_handler(self, payload):
        LOGGER.info("shutdown service")
        # 模拟键盘ctrl+c进行服务停止，如果你有更优雅的方法，可以将其改进
        raise KeyboardInterrupt

    @event_handler(ManageService.name, name + "close_one_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_one_event_handler(self, payload):
        """
        这里使用redis的分布式锁来进行单一服务实例的关闭，
        哪个实例抢到了redis分布式锁则执行关闭动作，没有抢到锁的继续运行。

        可能你会觉得，为什么不直接声明一个rpc式的调用，接收到rpc调用的实例直接停止自身不就好了，
        但是在没有AI微服务实例正在运行的场景下，调用方进行rpc调用会被阻塞，此后如果有实例被新拉起，则实例会立刻接收到该rpc调用而被停止服务。
        这涉及到nameko和rabbitmq的底层原理，我猜测是rpc的调用消息滞留在了消息队列中，导致新的实例启动后立刻拉到这个rpc消息而执行相应的调用。
        """
        LOGGER.info("receive close one event")
        close_unique_id = payload
        LOGGER.info(f"close_unique_id = {close_unique_id}")
        lock_ok = self.redis_storage.client.set(close_unique_id, "locked", ex=timedelta(minutes=1), nx=True)
        if lock_ok:
            return self.close_event_handler()
        else:
            LOGGER.info("close lock failed, continue running...")

    @event_handler(ManageService.name, name + "state_change", handler_type=BROADCAST, reliable_delivery=False)
    def state_to_ready_handler(self, payload):
        """
        在异步调用的场景下，需要在任务计算结束后通知AI微服务实例更新自己的服务状态，以便接收后续的调用
        """
        if self.unique_id == payload:
            self.state_lock.acquire()
            self.service_info.state = ServiceReadyState
            self.state_lock.release()

    @rpc
    def call(self, args: dict):
        """
        核心函数，同时也是模板方法模式的核心模板，定义了标准的调用流程和参数处理方法。
        """
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
                self.mqtt_storage.push_message(
                    json.dumps(output, default=lambda o: o.__json__() if hasattr(o, '__json__') else o.__dict__)
                )
                return output
            elif supportInput.type == MULTIPLE_PICTURE_URL_TYPE:
                img_urls = supportInput.value
                merged_result = {}
                for img_url in img_urls:
                    result = self.handle_single_image(img_url)
                    AIBaseService.merge_single_result(merged_result, result)
                output.update(merged_result)
                self.mqtt_storage.push_message(
                    json.dumps(output, default=lambda o: o.__json__() if hasattr(o, '__json__') else o.__dict__)
                )
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
        single_image的返回值示例如下，字典中的值需要是一个列表，否则在merge_single_result函数执行时会报错。

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
            LOGGER.info(f"Folder '{output_path}' created successfully.")
            # 这里使用【self】.single_image_cpp_call来进行函数调用而不是AIBaseService.single_image_cpp_call
            # 目的是为了将函数调用动态分派，调用子类的实现函数。下同。
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

        # 这里为什么使用多进程进行调用，是因为多线程情况下，cpp侧在计算的时候不会让出cpu，导致服务无法接收其他请求（如服务信息上报事件响应等）
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

        if 'taskId' not in self.args:
            raise ValueError("task id not found!")
        task_id = self.args['taskId']
        output_video_path = f"temp/output_{task_id}_{camera_id}.mp4"
        output_jsonl_path = f"temp/output_{task_id}.jsonl"

        multiprocessing.Process(target=self.camera_cpp_call, daemon=True,
                                args=[camera_id, self.hyperparameters, stop_signal_key,
                                      camera_data_queue_name, log_key, task_id, self.unique_id,
                                      output_video_path, output_jsonl_path]).start()

    @staticmethod
    def camera_cpp_call(camera_id, hyperparameters, stop_signal_key,
                        camera_data_queue_name, log_key, task_id, service_unique_id,
                        camera_output_path, camera_output_json_path):
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
        """
        由于多进程进行传参时，无法将rpc对象以及redis client对象进行传递，所以只能重新创建对象来进行服务调用。
        如果你有更好的方法，可以将其改进。
        """
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
            mqtt_storage = MQTTStorage()
            mqtt_storage.setup()
            msg = {
                'task_id': task_id,
                'video_url': video_url,
                'json_url': json_url,
            }
            mqtt_storage.push_message(json.dumps(msg))
            mqtt_storage.client.loop_write()
            cluster_rpc.manage_service.change_state_to_ready(service_name, service_unique_id)
            LOGGER.info(f"video task done, task_id:{task_id}")

    @staticmethod
    def after_camera_call(camera_output_path, camera_output_json_path, task_id, service_name, service_unique_id):
        with ClusterRpcProxy(config.get_rpc_config()) as cluster_rpc:
            video_url = cluster_rpc.object_storage_service.upload_object(camera_output_path)
            json_url = cluster_rpc.object_storage_service.upload_object(camera_output_json_path)

            mqtt_storage = MQTTStorage()
            mqtt_storage.setup()
            msg = {
                'task_id': task_id,
                'video_url': video_url,
                'json_url': json_url,
            }
            LOGGER.info(f"msg = {msg}")
            mqtt_storage.push_message(json.dumps(msg))
            mqtt_storage.client.loop(timeout=1)
            cluster_rpc.manage_service.change_state_to_ready(service_name, service_unique_id)
            LOGGER.info(f"camera task done, task_id:{task_id}")
