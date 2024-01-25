from nameko.events import event_handler, BROADCAST

from ais.yolo_cls import YoloClsArg, call_cls_yolo
from common.util import get_log_from_redis, clear_video_temp_resource, create_redis_client, clear_camera_temp_resource
from microservice.ai_base import AIBaseService
from model.ai_model import AIModel
from model.service_info import ServiceInfo
from model.support_input import *


def init_state_info():
    serviceInfo = ServiceInfo()

    model = AIModel()
    model.field = "分类"
    model.hyperparameters = []
    model.name = "yoloV8-cls"
    model.support_input = [SINGLE_PICTURE_URL_TYPE, MULTIPLE_PICTURE_URL_TYPE, VIDEO_URL_TYPE, CAMERA_TYPE]

    serviceInfo.model = model
    return serviceInfo


class RecognitionService(AIBaseService):
    name = "recognition_service"

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
            arg = YoloClsArg(camera_id=camera_id,
                             stop_signal_key=stop_signal_key, queue_name=camera_data_queue_name,
                             hyperparameters=hyperparameters, log_key=log_key)
            call_cls_yolo(arg)
            AIBaseService.after_camera_call(camera_output_path, camera_output_json_path,
                                            task_id, RecognitionService.name, service_unique_id)
        finally:
            clear_camera_temp_resource(camera_output_path, camera_output_json_path)


    @staticmethod
    def single_image_cpp_call(img_path, output_path, hyperparameters):
        arg = YoloClsArg(img_path=img_path, hyperparameters=hyperparameters)

        redis_client = create_redis_client()
        log_strs = get_log_from_redis(redis_client, arg.log_key)

        frames = call_cls_yolo(arg)
        return {
            'frames': frames,
            'logs': log_strs,
        }

    @staticmethod
    def video_cpp_call(video_path, video_output_path, video_output_json_path, video_progress_key,
                       hyperparameters, task_id, service_unique_id):
        try:
            arg = YoloClsArg(video_path=video_path, hyperparameters=hyperparameters,
                             video_output_path=video_output_path,
                             video_output_json_path=video_output_json_path,
                             video_progress_key=video_progress_key,
                             )
            call_cls_yolo(arg)
            AIBaseService.after_video_call(video_output_path, video_output_json_path,
                             task_id, RecognitionService.name, service_unique_id)
        finally:
            clear_video_temp_resource(video_path, video_output_path, video_output_json_path)
