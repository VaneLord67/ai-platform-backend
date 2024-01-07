import threading
import threading
import uuid

from nameko.events import event_handler, BROADCAST
from nameko.rpc import rpc, RpcProxy

from ais.yolo import YoloArg, call_yolo
from common.util import connect_to_database, clear_video_temp_resource
from microservice.ai_common import handle_video, handle_camera, call_init, parse_hyperparameters, after_video_call
from microservice.object_storage import ObjectStorageService
from microservice.redis_storage import RedisStorage
from microservice.service_default import default_state_change_handler, default_close_event_handler, \
    default_close_one_event_handler, default_state_report_handler
from model.ai_model import AIModel
from model.hyperparameter import Hyperparameter
from model.service_info import ServiceInfo, ServiceReadyState
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
    model.field = "跟踪"
    model.hyperparameters = [hp_batch_size, hp_size]
    model.name = "yoloV8"
    model.support_input = [VIDEO_URL_TYPE, CAMERA_TYPE]

    service_info.model = model
    return service_info


class TrackService:
    name = "track_service"

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
            if supportInput.type == VIDEO_URL_TYPE:
                handle_video(TrackService.handle_video, args, hyperparameters, self.unique_id)
                output['task_id'] = args['taskId']
                return output
            elif supportInput.type == CAMERA_TYPE:
                handle_camera(TrackService.handle_camera, args, hyperparameters)
                return output
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
        arg = YoloArg(camera_id=camera_id, stop_signal_key=stop_signal_key,
                      queue_name=camera_data_queue_name, is_track=True, is_show=True,
                      hyperparameters=hyperparameters, log_key=log_key)
        call_yolo(arg)

    @staticmethod
    def handle_video(video_path, video_output_path, video_output_json_path, video_progress_key,
                     hyperparameters, task_id, service_unique_id):
        try:
            arg = YoloArg(video_path=video_path,
                          is_track=True,
                          hyperparameters=hyperparameters,
                          video_output_path=video_output_path,
                          video_output_json_path=video_output_json_path,
                          video_progress_key=video_progress_key,
                          )
            call_yolo(arg)
            after_video_call(video_output_path, video_output_json_path,
                             task_id, TrackService.name, service_unique_id)
        finally:
            clear_video_temp_resource(video_path, video_output_path, video_output_json_path)
