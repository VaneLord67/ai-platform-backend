import cv2
import numpy as np
from nameko.events import event_handler, BROADCAST

from ais import tensorrt_cls_pybind
from common.log import LOGGER
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

    video_script_name = "scripts/recognition_video.py"
    camera_script_name = "scripts/recognition_camera.py"

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
    def single_image_cpp_call(img_path, output_path, hyperparameters):
        img = cv2.imread(img_path)
        log_strs = []
        box_json = []
        try:
            config = tensorrt_cls_pybind.ClassifierConfig()
            config.model_file_path = "E:/GraduationDesign/yolov8n-cls.trt"
            model = tensorrt_cls_pybind.Classifier(config)
            idx, score = model.inference(np.asarray(img, dtype=np.uint8))
            box_json.append({
                'label': idx,
                'score': score,
            })
        except Exception as e:
            LOGGER.error(e)
            log_strs.append(str(e))
        return {
            'frames': [box_json],
            'logs': log_strs,
        }
