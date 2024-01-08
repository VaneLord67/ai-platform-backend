from nameko.events import event_handler, BROADCAST
from nameko.standalone.rpc import ClusterRpcProxy

from ais.yolo import YoloArg, call_yolo
from common import config
from common.util import find_any_file, get_log_from_redis, clear_video_temp_resource, create_redis_client
from microservice.ai_base import AIBaseService
from microservice.manage import ManageService
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
    model.field = "检测"
    model.hyperparameters = [hp_batch_size, hp_size]
    model.name = "yoloV8"
    model.support_input = [SINGLE_PICTURE_URL_TYPE, MULTIPLE_PICTURE_URL_TYPE, VIDEO_URL_TYPE, CAMERA_TYPE]

    service_info.model = model
    return service_info


class DetectionService(AIBaseService):
    name = "detection_service"

    service_info = init_state_info()

    @event_handler(ManageService.name, name + "state_report", handler_type=BROADCAST, reliable_delivery=False)
    def state_report(self, payload):
        super().state_report(payload)

    @event_handler(ManageService.name, name + "close_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_event_handler(self, payload):
        super().close_event_handler(payload)

    @event_handler(ManageService.name, name + "close_one_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_one_event_handler(self, payload):
        super().close_event_handler(payload)

    @event_handler(ManageService.name, name + "state_change", handler_type=BROADCAST, reliable_delivery=False)
    def state_to_ready_handler(self, payload):
        super().state_to_ready_handler(payload)

    @staticmethod
    def camera_cpp_call(camera_id, hyperparameters, stop_signal_key, camera_data_queue_name, log_key):
        yolo_arg = YoloArg(camera_id=camera_id,
                           stop_signal_key=stop_signal_key,
                           queue_name=camera_data_queue_name,
                           is_show=True,
                           save_path=None,
                           hyperparameters=hyperparameters,
                           log_key=log_key)
        call_yolo(yolo_arg)

    @staticmethod
    def video_cpp_call(video_path, video_output_path, video_output_json_path, video_progress_key,
                       hyperparameters, task_id, service_unique_id):
        try:
            yolo_arg = YoloArg(video_path=video_path,
                               hyperparameters=hyperparameters,
                               video_output_path=video_output_path,
                               video_output_json_path=video_output_json_path,
                               video_progress_key=video_progress_key,
                               )
            call_yolo(yolo_arg)
            AIBaseService.after_video_call(video_output_path, video_output_json_path,
                                           task_id, DetectionService.name, service_unique_id)
        finally:
            clear_video_temp_resource(video_path, video_output_path, video_output_json_path)

    @staticmethod
    def single_image_cpp_call(img_path, output_path, hyperparameters):
        yolo_arg = YoloArg(img_path=img_path, save_path=output_path, hyperparameters=hyperparameters)
        frames = call_yolo(yolo_arg)
        output_img_path = find_any_file(output_path)

        redis_client = create_redis_client()
        log_strs = get_log_from_redis(redis_client, yolo_arg.log_key)

        with ClusterRpcProxy(config.get_rpc_config()) as cluster_rpc:
            urls = [cluster_rpc.object_storage_service.upload_object(output_img_path)]
        return {
            'urls': urls,
            'logs': log_strs,
            'frames': frames,
        }
