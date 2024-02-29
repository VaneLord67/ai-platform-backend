import cv2
from nameko.events import event_handler, BROADCAST
from nameko.standalone.rpc import ClusterRpcProxy

from ais.yolo_hx import inference, parse_results, draw_results, parsed_to_json
from common import config
from microservice.ai_base import AIBaseService
from microservice.manage import ManageService
from model.ai_model import AIModel
from model.service_info import ServiceInfo
from model.support_input import *


def init_state_info():
    service_info = ServiceInfo()

    model = AIModel()
    model.field = "检测"
    model.hyperparameters = []
    model.name = "yoloV8"
    model.support_input = [SINGLE_PICTURE_URL_TYPE, MULTIPLE_PICTURE_URL_TYPE, VIDEO_URL_TYPE, CAMERA_TYPE]

    service_info.model = model
    return service_info


class DetectionService(AIBaseService):
    name = "detection_service"

    service_info = init_state_info()

    video_script_name = "scripts/detection_hx_video.py"
    camera_script_name = "scripts/detection_hx_camera.py"

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
    def single_image_cpp_call(img_path, output_path, hyperparameters):
        img = cv2.imread(img_path)
        results, input_images = inference(img)
        frames = parse_results(results)
        output_img_path = output_path + "_0.jpg"
        draw_results(input_images, results, output_img_path)

        with ClusterRpcProxy(config.get_rpc_config()) as cluster_rpc:
            urls = [cluster_rpc.object_storage_service.upload_object(output_img_path)]
        return {
            'urls': urls,
            'logs': [],
            'frames': parsed_to_json(frames),
        }
