import os
import shutil
import threading
import time
import uuid

from nameko.events import event_handler, BROADCAST, SERVICE_POOL
from nameko.rpc import rpc, RpcProxy

from ais.yolo import YoloArg, call_yolo
from common.util import connect_to_database, download_file, find_any_file
from microservice.object_storage import ObjectStorageService
from microservice.redis_storage import RedisStorage
from model.ai_model import AIModel
from model.detection_output import DetectionOutput
from model.hyperparameter import Hyperparameter
from model.service_info import ServiceInfo, ServiceReadyState, ServiceRunningState
from model.support_input import *


def initStateInfo():
    serviceInfo = ServiceInfo()

    hyperparameter = Hyperparameter()
    hyperparameter.type = "integer"
    hyperparameter.name = "置信度阈值"

    model = AIModel()
    model.field = "检测"
    model.hyperparameters = [hyperparameter]
    model.name = "yoloV8"
    model.support_input = [SINGLE_PICTURE_URL_TYPE]

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

    @event_handler("manage_service", name + "close_one_event", handler_type=SERVICE_POOL, reliable_delivery=False)
    def close_one_event_handler(self, payload):
        print("receive close one event")
        raise KeyboardInterrupt

    @rpc
    def detectRPCHandler(self, args: dict):
        self.state_lock.acquire()
        try:
            self.serviceInfo.state = ServiceRunningState
            if 'hyperparameters' in args:
                hps = args['hyperparameters']
                hyperparameters = []
                for hp in hps:
                    hyperparameters.append(Hyperparameter().from_dict(hp))

            supportInput = SupportInput().from_dict(args['supportInput'])
            output = DetectionOutput()
            urls = []
            if supportInput.type == SINGLE_PICTURE_URL_TYPE:
                # handle input
                pic_url = supportInput.value
                img_name, img_path = download_file(pic_url)
                unique_id = str(uuid.uuid4())
                output_path = f"temp/{img_name}_{unique_id}/"
                # 创建文件夹
                try:
                    os.makedirs(output_path, exist_ok=True)
                    print(f"Folder '{output_path}' created successfully.")

                    yolo_arg = YoloArg(img_path=img_path, save_path=output_path)
                    frames = call_yolo(yolo_arg)
                    output.frames = frames
                    output_img_path = find_any_file(output_path)

                    url = self.objectStorageService.upload_object(output_img_path)
                    urls.append(url)
                    output.urls = urls
                    return output
                finally:
                    if os.path.exists(img_path):
                        try:
                            os.remove(img_path)
                            print(f'File {img_path} deleted successfully.')
                        except OSError as e:
                            print(f'Error deleting file {img_path}: {e}')
                    shutil.rmtree(output_path)
                    print(f"Folder '{output_path}' deleted successfully.")
            return output
        finally:
            self.serviceInfo.state = ServiceReadyState
            self.state_lock.release()
