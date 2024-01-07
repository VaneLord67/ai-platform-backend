import os
import threading
import time
import uuid

from nameko.events import event_handler, BROADCAST
from nameko.rpc import rpc, RpcProxy

from ais.yolo import YoloArg, call_yolo
from common.util import connect_to_database, download_file, find_any_file, clear_image_temp_resource, \
    get_log_from_redis, clear_video_temp_resource
from microservice.ai_common import handle_video, handle_camera, after_video_call
from microservice.object_storage import ObjectStorageService
from microservice.redis_storage import RedisStorage
from microservice.service_default import default_state_change_handler, default_state_report_handler, \
    default_close_event_handler, default_close_one_event_handler
from model.ai_model import AIModel
from model.detection_output import DetectionOutput
from model.hyperparameter import Hyperparameter
from model.service_info import ServiceInfo, ServiceReadyState, ServiceRunningState
from model.support_input import *


def init_state_info():
    service_info = ServiceInfo()

    hp_batch_size = Hyperparameter()
    hp_batch_size.type = "integer"
    hp_batch_size.name = "batch_size"
    hp_batch_size.default = 1

    hp_size = Hyperparameter()
    hp_size.type = "integer"
    hp_size.name = "size"
    hp_size.default = 640

    model = AIModel()
    model.field = "检测"
    model.hyperparameters = [hp_batch_size, hp_size]
    model.name = "yoloV8"
    model.support_input = [SINGLE_PICTURE_URL_TYPE, MULTIPLE_PICTURE_URL_TYPE, VIDEO_URL_TYPE, CAMERA_TYPE]

    service_info.model = model
    return service_info


class DetectionService:
    name = "detection_service"

    unique_id = str(uuid.uuid4())
    service_info = init_state_info()
    state_lock = threading.Lock()

    redis_storage = RedisStorage()

    object_storage_service = RpcProxy(ObjectStorageService.name)

    def __init__(self):
        self.conn = connect_to_database()

    @event_handler("manage_service", name + "state_report", handler_type=BROADCAST, reliable_delivery=False)
    def state_report(self, payload):
        default_state_report_handler(payload, self.state_lock, self.service_info, self.redis_storage.client)

    @event_handler("manage_service", name + "close_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_event_handler(self, payload):
        default_close_event_handler()

    @event_handler("manage_service", name + "close_one_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_one_event_handler(self, payload):
        default_close_one_event_handler(payload, self.redis_storage.client)

    @rpc
    def call(self, args: dict):
        self.state_lock.acquire()
        supportInput = SupportInput().from_dict(args['supportInput'])
        try:
            output = DetectionOutput()
            output.unique_id = self.unique_id
            if self.service_info.state != ServiceReadyState:
                output.busy = True
                return output
            self.service_info.task_start_time = int(time.time() * 1000)
            self.service_info.state = ServiceRunningState
            hyperparameters = []
            if 'hyperparameters' in args:
                hps = args['hyperparameters']
                for hp in hps:
                    hyperparameters.append(Hyperparameter().from_dict(hp))
            urls = []
            frames = []
            log_strs = []
            self.service_info.task_type = supportInput.type
            if supportInput.type == SINGLE_PICTURE_URL_TYPE:
                img_url = supportInput.value
                urls, frames, log_strs = self.handle_single_image(img_url, hyperparameters)
            elif supportInput.type == MULTIPLE_PICTURE_URL_TYPE:
                img_urls = supportInput.value
                urls = []
                frames = []
                for img_url in img_urls:
                    single_urls, single_frames, single_logs = self.handle_single_image(img_url, hyperparameters)
                    urls.extend(single_urls)
                    frames.extend(single_frames)
                    log_strs.extend(single_logs)
            elif supportInput.type == VIDEO_URL_TYPE:
                handle_video(DetectionService.handle_video, args, hyperparameters, self.unique_id)
                output.task_id = args['taskId']
            elif supportInput.type == CAMERA_TYPE:
                handle_camera(DetectionService.handle_camera, args, hyperparameters)
            output.urls = urls
            output.frames = frames
            output.logs = log_strs
            return output
        finally:
            if supportInput.type not in [CAMERA_TYPE, VIDEO_URL_TYPE]:
                self.service_info.state = ServiceReadyState
            self.state_lock.release()

    @event_handler("manage_service", name + "state_change", handler_type=BROADCAST, reliable_delivery=False)
    def state_change_handler(self, payload):
        default_state_change_handler(self.unique_id, payload, self.state_lock, self.service_info, ServiceReadyState)

    @staticmethod
    def handle_camera(camera_id, hyperparameters, stop_signal_key, camera_data_queue_name, log_key):
        yolo_arg = YoloArg(camera_id=camera_id, stop_signal_key=stop_signal_key, queue_name=camera_data_queue_name,
                           is_show=True, save_path=None, hyperparameters=hyperparameters, log_key=log_key)
        call_yolo(yolo_arg)

    @staticmethod
    def handle_video(video_path, video_output_path, video_output_json_path, video_progress_key,
                     hyperparameters, task_id, service_unique_id):
        try:
            yolo_arg = YoloArg(video_path=video_path,
                               hyperparameters=hyperparameters,
                               video_output_path=video_output_path,
                               video_output_json_path=video_output_json_path,
                               video_progress_key=video_progress_key,
                               )
            call_yolo(yolo_arg)
            after_video_call(video_output_path, video_output_json_path,
                             task_id, DetectionService.name, service_unique_id)
        finally:
            clear_video_temp_resource(video_path, video_output_path, video_output_json_path)

    def handle_single_image(self, img_url, hyperparameters):
        img_name, img_path = download_file(img_url)
        unique_id = str(uuid.uuid4())
        output_path = f"temp/{img_name}_{unique_id}/"
        try:
            os.makedirs(output_path, exist_ok=True)
            print(f"Folder '{output_path}' created successfully.")

            yolo_arg = YoloArg(img_path=img_path, save_path=output_path, hyperparameters=hyperparameters)
            frames = call_yolo(yolo_arg)
            output_img_path = find_any_file(output_path)

            log_strs = get_log_from_redis(self.redis_storage.client, yolo_arg.log_key)

            urls = [self.object_storage_service.upload_object(output_img_path)]
            return urls, frames, log_strs
        finally:
            clear_image_temp_resource(img_path, output_path)
