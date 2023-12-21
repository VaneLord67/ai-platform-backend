import base64
import multiprocessing
import os
import shutil
import threading
import uuid
from datetime import timedelta

import cv2
from nameko.events import event_handler, BROADCAST
from nameko.rpc import rpc, RpcProxy

from ais.opencv_track import TrackArg, call_track
from common.util import connect_to_database, download_file, generate_video, get_video_fps
from microservice.object_storage import ObjectStorageService
from microservice.redis_storage import RedisStorage
from model.ai_model import AIModel
from model.hyperparameter import Hyperparameter
from model.service_info import ServiceInfo, ServiceReadyState, ServiceRunningState
from model.support_input import *


def initStateInfo():
    serviceInfo = ServiceInfo()

    hp_roi_x = Hyperparameter()
    hp_roi_x.type = 'integer'
    hp_roi_x.name = 'roi_x'
    hp_roi_x.default = 0

    hp_roi_y = Hyperparameter()
    hp_roi_y.type = 'integer'
    hp_roi_y.name = 'roi_y'
    hp_roi_y.default = 0

    hp_roi_width = Hyperparameter()
    hp_roi_width.type = 'integer'
    hp_roi_width.name = 'roi_width'
    hp_roi_width.default = 0

    hp_roi_height = Hyperparameter()
    hp_roi_height.type = 'integer'
    hp_roi_height.name = 'roi_height'
    hp_roi_height.default = 0

    model = AIModel()
    model.field = "跟踪"
    model.hyperparameters = [hp_roi_x, hp_roi_y, hp_roi_width, hp_roi_height]
    model.name = "MIL"
    model.support_input = [VIDEO_URL_TYPE, CAMERA_TYPE]

    serviceInfo.model = model
    return serviceInfo


class TrackService:
    name = "track_service"

    unique_id = str(uuid.uuid4())
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
    def track(self, args: dict):
        self.state_lock.acquire()
        supportInput = SupportInput().from_dict(args['supportInput'])
        try:
            self.serviceInfo.state = ServiceRunningState
            hyperparameters = []
            if 'hyperparameters' in args:
                hps = args['hyperparameters']
                for hp in hps:
                    hyperparameters.append(Hyperparameter().from_dict(hp))
            frames = []
            url = ""
            if supportInput.type == VIDEO_URL_TYPE:
                video_url = supportInput.value
                url, frames = self.handleVideo(video_url, hyperparameters)
            elif supportInput.type == CAMERA_TYPE:
                camera_id = supportInput.value
                stop_signal_key = args['stopSignalKey']
                camera_data_queue_name = args['queueName']
                roi_key = args['roiKey']
                self.redis_storage.client.expire(name=camera_data_queue_name, time=timedelta(hours=24))
                multiprocessing.Process(target=TrackService.handleCamera,
                                        args=[camera_id, hyperparameters, stop_signal_key,
                                              camera_data_queue_name, roi_key]).start()
            output = {
                "url": url,
                "frames": frames,
                "unique_id": self.unique_id
            }
            return output
        finally:
            if supportInput.type != CAMERA_TYPE:
                self.serviceInfo.state = ServiceReadyState
            self.state_lock.release()

    @event_handler("manage_service", name + "state_change", handler_type=BROADCAST, reliable_delivery=False)
    def cameraStateChangeHandler(self, payload):
        if self.unique_id == payload:
            self.state_lock.acquire()
            self.serviceInfo.state = ServiceReadyState
            self.state_lock.release()

    @staticmethod
    def handleCamera(camera_id, hyperparameters, stop_signal_key, camera_data_queue_name, roi_key):
        arg = TrackArg(cam_id=camera_id, stop_signal_key=stop_signal_key,
                       queue_name=camera_data_queue_name, roi_key=roi_key,
                       hyperparameters=hyperparameters)
        call_track(arg)

    @rpc
    def stopCamera(self, stop_signal_key):
        client = self.redis_storage.client
        print(f"set {stop_signal_key}")
        client.set(stop_signal_key, "1", ex=timedelta(hours=1))

    def handleVideo(self, video_url, hyperparameters):
        video_fps = get_video_fps(video_url)
        video_name, video_path = download_file(video_url)
        unique_id = str(uuid.uuid4())
        output_path = f"temp/{video_name}_{unique_id}/"
        output_video_path = f"temp/output_{video_name}"
        try:
            os.makedirs(output_path, exist_ok=True)
            print(f"Folder '{output_path}' created successfully.")

            arg = TrackArg(video_path=video_path, save_path=output_path, hyperparameters=hyperparameters)
            frames = call_track(arg)

            generate_video(output_video_path=output_video_path, folder_path=output_path, fps=video_fps)

            url = self.objectStorageService.upload_object(output_video_path)
            print("upload video:", url)
            return url, frames
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

    @rpc
    def get_first_frame(self, video_url: str):
        video_url = video_url.strip()
        # 读取视频文件
        cap = cv2.VideoCapture(video_url)
        # 检查视频是否成功打开
        if not cap.isOpened():
            print("Error: Could not open video file: ", video_url)
            return None
        # 读取第一帧
        ret, frame = cap.read()
        # 关闭视频文件
        cap.release()
        # 检查是否成功读取第一帧
        if not ret:
            print("Error: Could not read the first frame.")
            return None
        # 将图像编码为Base64
        _, buffer = cv2.imencode('.jpg', frame)
        base64_encoded = base64.b64encode(buffer)
        return base64_encoded.decode('utf-8')
