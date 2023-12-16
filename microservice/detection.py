import os
import shutil
import threading
import uuid
from datetime import timedelta

from nameko.events import event_handler, BROADCAST
from nameko.rpc import rpc, RpcProxy

from ais.yolo import YoloArg, call_yolo
from common.util import connect_to_database, download_file, find_any_file, generate_video
from microservice.load_dependency import LoadDependency
from microservice.object_storage import ObjectStorageService
from microservice.redis_storage import RedisStorage
from model.ai_model import AIModel
from model.detection_output import DetectionOutput
from model.hyperparameter import Hyperparameter
from model.service_info import ServiceInfo, ServiceReadyState, ServiceRunningState
from model.support_input import *


def initStateInfo():
    serviceInfo = ServiceInfo()

    hp_batch_size = Hyperparameter()
    hp_batch_size.type = "integer"
    hp_batch_size.name = "batch_size"

    hp_size = Hyperparameter()
    hp_size.type = "integer"
    hp_size.name = "size"

    model = AIModel()
    model.field = "检测"
    model.hyperparameters = [hp_batch_size, hp_size]
    model.name = "yoloV8"
    model.support_input = [SINGLE_PICTURE_URL_TYPE, MULTIPLE_PICTURE_URL_TYPE, VIDEO_URL_TYPE]

    serviceInfo.model = model
    return serviceInfo


class DetectionService:
    name = "detection_service"

    serviceInfo = initStateInfo()
    state_lock = threading.Lock()

    redis_storage = RedisStorage()

    objectStorageService = RpcProxy(ObjectStorageService.name)

    def __init__(self):
        self.conn = connect_to_database()

    @event_handler("manage_service", name + "state_report", handler_type=BROADCAST, reliable_delivery=False)
    def state_report(self, payload):
        redis_list_key = payload
        self.state_lock.acquire()
        try:
            state_string = self.serviceInfo.__str__()
            self.redis_storage.client.rpush(redis_list_key, state_string)
        finally:
            self.state_lock.release()

    @event_handler("manage_service", name + "close_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_event_handler(self, payload):
        print("receive close event")
        raise KeyboardInterrupt

    @event_handler("manage_service", name + "close_one_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_one_event_handler(self, payload):
        print("receive close one event")
        close_unique_id = payload
        redis_client = self.redis_storage.client
        print(f"close_unique_id = {close_unique_id}")
        lock_ok = redis_client.set(close_unique_id, "locked", ex=timedelta(minutes=1), nx=True)
        if lock_ok:
            print("get close lock, raise KeyboardInterrupt...")
            raise KeyboardInterrupt
        else:
            print("close lock failed, continue running...")

    @rpc
    def detectRPCHandler(self, args: dict):
        self.state_lock.acquire()
        try:
            self.serviceInfo.state = ServiceRunningState
            hyperparameters = []
            if 'hyperparameters' in args:
                hps = args['hyperparameters']
                for hp in hps:
                    hyperparameters.append(Hyperparameter().from_dict(hp))

            supportInput = SupportInput().from_dict(args['supportInput'])
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
            output.urls = urls
            output.frames = frames
            return output
        finally:
            self.serviceInfo.state = ServiceReadyState
            self.state_lock.release()

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

            urls = [self.objectStorageService.upload_object(output_video_path)]
            return urls, frames
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

            urls = [self.objectStorageService.upload_object(output_img_path)]
            return urls, frames
        finally:
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                    print(f'File {img_path} deleted successfully.')
                except OSError as e:
                    print(f'Error deleting file {img_path}: {e}')
            shutil.rmtree(output_path)
            print(f"Folder '{output_path}' deleted successfully.")
