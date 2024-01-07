import os
import threading
import uuid

from nameko.events import event_handler, BROADCAST
from nameko.rpc import rpc, RpcProxy

from ais.yolo_cls import YoloClsArg, call_cls_yolo
from common.util import connect_to_database, download_file, clear_image_temp_resource, \
    get_log_from_redis, clear_video_temp_resource
from microservice.ai_common import handle_video, handle_camera, call_init, parse_hyperparameters, after_video_call
from microservice.object_storage import ObjectStorageService
from microservice.redis_storage import RedisStorage
from microservice.service_default import default_state_change_handler, default_state_report_handler, \
    default_close_event_handler, default_close_one_event_handler
from model.ai_model import AIModel
from model.service_info import ServiceInfo, ServiceReadyState
from model.support_input import *


def init_state_info():
    serviceInfo = ServiceInfo()

    model = AIModel()
    model.field = "分类"
    model.hyperparameters = []
    model.name = "yolov8-cls"
    model.support_input = [SINGLE_PICTURE_URL_TYPE, MULTIPLE_PICTURE_URL_TYPE, VIDEO_URL_TYPE, CAMERA_TYPE]

    serviceInfo.model = model
    return serviceInfo


class RecognitionService:
    name = "recognition_service"

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
            output = call_init(self.service_info, supportInput, self.unique_id)
            if output['busy']:
                return output
            hyperparameters = parse_hyperparameters(args)
            frames = []
            logs = []
            if supportInput.type == SINGLE_PICTURE_URL_TYPE:
                img_url = supportInput.value
                frames, logs = self.handle_single_image(img_url, hyperparameters)
            elif supportInput.type == MULTIPLE_PICTURE_URL_TYPE:
                img_urls = supportInput.value
                for img_url in img_urls:
                    single_frames, single_logs = self.handle_single_image(img_url, hyperparameters)
                    frames.extend(single_frames)
                    logs.extend(single_logs)
            elif supportInput.type == VIDEO_URL_TYPE:
                handle_video(RecognitionService.handle_video, args, hyperparameters, self.unique_id)
                output['task_id'] = args['taskId']
                return output
            elif supportInput.type == CAMERA_TYPE:
                handle_camera(RecognitionService.handle_camera, args, hyperparameters)
            output = {
                "busy": False,
                "frames": frames,
                "unique_id": self.unique_id,
                "logs": logs,
            }
            return output
        finally:
            if supportInput.type != CAMERA_TYPE:
                self.service_info.state = ServiceReadyState
            self.state_lock.release()

    @event_handler("manage_service", name + "state_change", handler_type=BROADCAST, reliable_delivery=False)
    def state_change_handler(self, payload):
        default_state_change_handler(self.unique_id, payload, self.state_lock, self.service_info, ServiceReadyState)

    @staticmethod
    def handle_camera(camera_id, hyperparameters, stop_signal_key, camera_data_queue_name, log_key):
        arg = YoloClsArg(camera_id=camera_id,
                         stop_signal_key=stop_signal_key, queue_name=camera_data_queue_name,
                         hyperparameters=hyperparameters, log_key=log_key)
        call_cls_yolo(arg)

    def handle_single_image(self, img_url, hyperparameters):
        img_name, img_path = download_file(img_url)
        unique_id = str(uuid.uuid4())
        output_path = f"temp/{img_name}_{unique_id}/"
        try:
            os.makedirs(output_path, exist_ok=True)
            print(f"Folder '{output_path}' created successfully.")

            arg = YoloClsArg(img_path=img_path, hyperparameters=hyperparameters)
            logs = get_log_from_redis(self.redis_storage.client, arg.log_key)
            clsResults = call_cls_yolo(arg)
            return clsResults, logs
        finally:
            clear_image_temp_resource(img_path, output_path)

    @staticmethod
    def handle_video(video_path, video_output_path, video_output_json_path, video_progress_key,
                     hyperparameters, task_id, service_unique_id):
        try:
            arg = YoloClsArg(video_path=video_path, hyperparameters=hyperparameters,
                             video_output_path=video_output_path,
                             video_output_json_path=video_output_json_path,
                             video_progress_key=video_progress_key,
                             )
            call_cls_yolo(arg)
            after_video_call(video_output_path, video_output_json_path,
                             task_id, RecognitionService.name, service_unique_id)
        finally:
            clear_video_temp_resource(video_path, video_output_path, video_output_json_path)

