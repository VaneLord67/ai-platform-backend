import multiprocessing
import os
import threading
import uuid
from datetime import timedelta

from nameko.events import event_handler, BROADCAST
from nameko.rpc import rpc, RpcProxy

from ais.yolo import YoloArg, call_yolo
from common.util import connect_to_database, download_file, find_any_file, generate_video, clear_video_temp_resource, \
    clear_image_temp_resource
from microservice.object_storage import ObjectStorageService
from microservice.redis_storage import RedisStorage
from microservice.service_default import default_state_change_handler, default_state_report_handler, \
    default_close_event_handler, default_close_one_event_handler
from model.ai_model import AIModel
from model.detection_output import DetectionOutput
from model.hyperparameter import Hyperparameter
from model.service_info import ServiceInfo, ServiceReadyState, ServiceRunningState
from model.support_input import *


def initStateInfo():
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
    service_info = initStateInfo()
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
    def detectRPCHandler(self, args: dict):
        self.state_lock.acquire()
        supportInput = SupportInput().from_dict(args['supportInput'])

        try:
            self.service_info.state = ServiceRunningState
            hyperparameters = []
            if 'hyperparameters' in args:
                hps = args['hyperparameters']
                for hp in hps:
                    hyperparameters.append(Hyperparameter().from_dict(hp))
            output = DetectionOutput()
            urls = []
            frames = []
            if supportInput.type == SINGLE_PICTURE_URL_TYPE:
                img_url = supportInput.value
                urls, frames = self.handleSingleImage(img_url, hyperparameters)
            elif supportInput.type == MULTIPLE_PICTURE_URL_TYPE:
                img_urls = supportInput.value
                urls = []
                frames = []
                for img_url in img_urls:
                    single_urls, single_frames = self.handleSingleImage(img_url, hyperparameters)
                    urls.extend(single_urls)
                    frames.extend(single_frames)
            elif supportInput.type == VIDEO_URL_TYPE:
                video_url = supportInput.value
                urls, frames = self.handleVideo(video_url, hyperparameters)
            elif supportInput.type == CAMERA_TYPE:
                camera_id = supportInput.value
                stop_signal_key = args['stopSignalKey']
                camera_data_queue_name = args['queueName']
                self.redis_storage.client.expire(name=camera_data_queue_name, time=timedelta(hours=24))
                output.unique_id = self.unique_id
                multiprocessing.Process(target=DetectionService.handleCamera, daemon=True,
                                        args=[camera_id, hyperparameters, stop_signal_key,
                                              camera_data_queue_name]).start()
            output.urls = urls
            output.frames = frames
            return output
        finally:
            if supportInput.type != CAMERA_TYPE:
                self.service_info.state = ServiceReadyState
            self.state_lock.release()

    @event_handler("manage_service", name + "state_change", handler_type=BROADCAST, reliable_delivery=False)
    def cameraStateChangeHandler(self, payload):
        default_state_change_handler(self.unique_id, payload, self.state_lock, self.service_info, ServiceReadyState)

    @staticmethod
    def handleCamera(camera_id, hyperparameters, stop_signal_key, camera_data_queue_name):
        yolo_arg = YoloArg(camera_id=camera_id, stop_signal_key=stop_signal_key, queue_name=camera_data_queue_name,
                           is_show=True, save_path=None, hyperparameters=hyperparameters)
        call_yolo(yolo_arg)

    def handleVideo(self, video_url, hyperparameters):
        video_name, video_path = download_file(video_url)
        unique_id = str(uuid.uuid4())
        output_path = f"temp/{video_name}_{unique_id}/"
        output_video_path = f"temp/output_{video_name}"
        try:
            os.makedirs(output_path, exist_ok=True)
            print(f"Folder '{output_path}' created successfully.")

            yolo_arg = YoloArg(video_path=video_path, save_path=output_path, hyperparameters=hyperparameters)
            frames = call_yolo(yolo_arg)

            generate_video(output_video_path=output_video_path, folder_path=output_path)

            urls = [self.object_storage_service.upload_object(output_video_path)]
            return urls, frames
        finally:
            clear_video_temp_resource(video_path, output_video_path, output_path)

    def handleSingleImage(self, img_url, hyperparameters):
        img_name, img_path = download_file(img_url)
        unique_id = str(uuid.uuid4())
        output_path = f"temp/{img_name}_{unique_id}/"
        try:
            os.makedirs(output_path, exist_ok=True)
            print(f"Folder '{output_path}' created successfully.")

            yolo_arg = YoloArg(img_path=img_path, save_path=output_path, hyperparameters=hyperparameters)
            frames = call_yolo(yolo_arg)
            output_img_path = find_any_file(output_path)

            urls = [self.object_storage_service.upload_object(output_img_path)]
            return urls, frames
        finally:
            clear_image_temp_resource(img_path, output_path)
