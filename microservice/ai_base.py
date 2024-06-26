import json
import os
import subprocess
import sys
import threading
import time
import uuid
from abc import ABC
from datetime import timedelta
from typing import List, Union

from nameko.events import event_handler, BROADCAST
from nameko.rpc import rpc

from common.log import LOGGER
from common.util import download_file, clear_image_temp_resource
from microservice.manage import ManageService
from microservice.mqtt_storage import MQTTStorage
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

    video_script_name = ""
    camera_script_name = ""

    unique_id = str(uuid.uuid4())
    service_info = ServiceInfo()
    state_lock = threading.Lock()

    redis_storage = RedisStorage()
    mqtt_storage = MQTTStorage()

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

        hyperparameter_json_str = json.dumps(self.hyperparameters,
                                             default=lambda o: o.__json__() if hasattr(o, '__json__') else o.__dict__)
        arg_to_subprocess = [video_path, output_video_path, output_jsonl_path, video_progress_key,
                             hyperparameter_json_str, task_id, self.unique_id]
        # 这里从sys获取解释器路径，可以兼容conda虚拟环境
        os.environ['PYTHONPATH'] = os.getcwd()
        interpreter_path = sys.executable
        # 相当于在命令行执行"python xx.py arg1 arg2..."
        # 因为Python的多进程(multiprocessing.Process)在Ubuntu系统下的实现是使用了fork系统调用，fork会复制父进程Nameko的环境
        # 导致子进程与rabbitmq进行连接，破坏父进程与rabbitmq的连接（因为占用了同样的channel和锁相关的资源）
        # 因此，这里选用subprocess.Popen，用执行命令的方法来启动子进程，这样子进程就不会拥有Nameko的环境，与父进程隔离开
        # 那么在这种方式下，传参的类型为字符串，需要将所有参数都转换为字符串再传递给子进程
        # 那么这里为什么使用多【进程】进行调用呢
        # 因为多【线程】情况下，cpp侧在计算的时候不会让出cpu，导致Nameko服务无法接收其他请求（如服务信息上报事件响应等）
        subprocess.Popen([interpreter_path, self.video_script_name] + arg_to_subprocess)

    @staticmethod
    def video_cpp_call(video_path, output_video_path, output_jsonl_path, video_progress_key,
                       hyperparameters, task_id, unique_id):
        raise NotImplementedError("please implement video_cpp_call")

    def handle_camera(self):
        camera_id = str(self.support_input.value)  # 传递给Popen的必须是字符串
        namespace = self.args['namespace']

        if 'taskId' not in self.args:
            raise ValueError("task id not found!")
        task_id = self.args['taskId']
        output_video_path = f"temp/output_{task_id}_camera.mp4"
        output_jsonl_path = f"temp/output_{task_id}.jsonl"

        hyperparameter_json_str = json.dumps(self.hyperparameters,
                                             default=lambda o: o.__json__() if hasattr(o, '__json__') else o.__dict__)
        arg_to_subprocess = [camera_id, hyperparameter_json_str, namespace,
                             task_id, self.unique_id, output_video_path, output_jsonl_path]
        os.environ['PYTHONPATH'] = os.getcwd()
        interpreter_path = sys.executable
        # 这里的设计与handle_video()相同
        subprocess.Popen([interpreter_path, self.camera_script_name] + arg_to_subprocess)

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
