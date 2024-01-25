from nameko.events import event_handler, BROADCAST

from ais.yolo import YoloArg, call_yolo
from common.util import clear_video_temp_resource, clear_camera_temp_resource
from microservice.ai_base import AIBaseService
from model.ai_model import AIModel
from model.hyperparameter import Hyperparameter
from model.service_info import ServiceInfo
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


class TrackService(AIBaseService):
    name = "track_service"

    service_info = init_state_info()

    @event_handler("manage_service", name + "state_report", handler_type=BROADCAST, reliable_delivery=False)
    def state_report(self, payload):
        super().state_report(payload)

    @event_handler("manage_service", name + "close_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_event_handler(self, payload):
        super().close_event_handler(payload)

    @event_handler("manage_service", name + "close_one_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_one_event_handler(self, payload):
        super().close_one_event_handler(payload)

    @event_handler("manage_service", name + "state_change", handler_type=BROADCAST, reliable_delivery=False)
    def state_to_ready_handler(self, payload):
        super().state_to_ready_handler(payload)

    @staticmethod
    def camera_cpp_call(camera_id, hyperparameters, stop_signal_key,
                        camera_data_queue_name, log_key, task_id, service_unique_id,
                        camera_output_path, camera_output_json_path):
        try:
            arg = YoloArg(camera_id=camera_id, stop_signal_key=stop_signal_key,
                          queue_name=camera_data_queue_name, is_track=True, is_show=True,
                          hyperparameters=hyperparameters, log_key=log_key)
            call_yolo(arg)
            AIBaseService.after_camera_call(camera_output_path, camera_output_json_path,
                                            task_id, TrackService.name, service_unique_id)
        finally:
            clear_camera_temp_resource(camera_output_path, camera_output_json_path)

    @staticmethod
    def video_cpp_call(video_path, video_output_path, video_output_json_path, video_progress_key,
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
            AIBaseService.after_video_call(video_output_path, video_output_json_path,
                                           task_id, TrackService.name, service_unique_id)
        finally:
            clear_video_temp_resource(video_path, video_output_path, video_output_json_path)
