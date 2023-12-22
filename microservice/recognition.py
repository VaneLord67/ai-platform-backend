import multiprocessing
import os
import shutil
import threading
import uuid
from datetime import timedelta

from nameko.events import event_handler, BROADCAST
from nameko.rpc import rpc, RpcProxy

from ais.yolo_cls import YoloClsArg, call_cls_yolo
from common.util import connect_to_database, download_file
from microservice.object_storage import ObjectStorageService
from microservice.redis_storage import RedisStorage
from microservice.service_default import default_state_change_handler, default_state_report_handler, \
    default_close_event_handler, default_close_one_event_handler
from model.ai_model import AIModel
from model.hyperparameter import Hyperparameter
from model.service_info import ServiceInfo, ServiceReadyState, ServiceRunningState
from model.support_input import *


def initStateInfo():
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
    def call(self, args: dict):
        self.state_lock.acquire()
        supportInput = SupportInput().from_dict(args['supportInput'])
        try:
            self.service_info.state = ServiceRunningState
            hyperparameters = []
            if 'hyperparameters' in args:
                hps = args['hyperparameters']
                for hp in hps:
                    hyperparameters.append(Hyperparameter().from_dict(hp))
            frames = []
            if supportInput.type == SINGLE_PICTURE_URL_TYPE:
                img_url = supportInput.value
                frames = RecognitionService.handleSingleImage(img_url, hyperparameters)
            elif supportInput.type == MULTIPLE_PICTURE_URL_TYPE:
                img_urls = supportInput.value
                for img_url in img_urls:
                    single_frames = RecognitionService.handleSingleImage(img_url, hyperparameters)
                    frames.extend(single_frames)
            elif supportInput.type == VIDEO_URL_TYPE:
                video_url = supportInput.value
                frames = RecognitionService.handleVideo(video_url, hyperparameters)
            elif supportInput.type == CAMERA_TYPE:
                camera_id = supportInput.value
                stop_signal_key = args['stopSignalKey']
                camera_data_queue_name = args['queueName']
                self.redis_storage.client.expire(name=camera_data_queue_name, time=timedelta(hours=24))
                multiprocessing.Process(target=RecognitionService.handleCamera,
                                        args=[camera_id, hyperparameters, stop_signal_key,
                                              camera_data_queue_name]).start()
            output = {
                "frames": frames,
                "unique_id": self.unique_id
            }
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
        arg = YoloClsArg(camera_id=camera_id,
                         stop_signal_key=stop_signal_key, queue_name=camera_data_queue_name,
                         hyperparameters=hyperparameters)
        call_cls_yolo(arg)

    @staticmethod
    def handleSingleImage(img_url, hyperparameters):
        img_name, img_path = download_file(img_url)
        unique_id = str(uuid.uuid4())
        output_path = f"temp/{img_name}_{unique_id}/"
        try:
            os.makedirs(output_path, exist_ok=True)
            print(f"Folder '{output_path}' created successfully.")

            arg = YoloClsArg(img_path=img_path, hyperparameters=hyperparameters)
            clsResults = call_cls_yolo(arg)
            return clsResults
        finally:
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                    print(f'File {img_path} deleted successfully.')
                except OSError as e:
                    print(f'Error deleting file {img_path}: {e}')
            shutil.rmtree(output_path)
            print(f"Folder '{output_path}' deleted successfully.")

    @staticmethod
    def handleVideo(video_url, hyperparameters):
        video_name, video_path = download_file(video_url)
        unique_id = str(uuid.uuid4())
        output_path = f"temp/{video_name}_{unique_id}/"
        output_video_path = f"temp/output_{video_name}"
        try:
            os.makedirs(output_path, exist_ok=True)
            print(f"Folder '{output_path}' created successfully.")

            arg = YoloClsArg(video_path=video_path, hyperparameters=hyperparameters)
            frames = call_cls_yolo(arg)

            return frames
        finally:
            if os.path.exists(video_path):
                try:
                    os.remove(video_path)
                    print(f'File {video_path} deleted successfully.')
                except OSError as e:
                    print(f'Error deleting file {video_path}: {e}')
            if os.path.exists(output_video_path):
                try:
                    os.remove(output_video_path)
                    print(f'File {output_video_path} deleted successfully.')
                except OSError as e:
                    print(f'Error deleting file {output_video_path}: {e}')
            shutil.rmtree(output_path)
            print(f"Folder '{output_path}' deleted successfully.")
