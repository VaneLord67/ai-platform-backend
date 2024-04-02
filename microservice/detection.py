import cv2
import numpy as np
from nameko.events import event_handler, BROADCAST
from nameko.standalone.rpc import ClusterRpcProxy

from ais import tensorrt_alpha_pybind
from common import config
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

    video_script_name = "scripts/detection_video.py"
    camera_script_name = "scripts/detection_camera.py"

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
        log_strs = []
        img = cv2.imread(img_path)
        try:
            width, height = img.shape[1], img.shape[0]
            detector_config = tensorrt_alpha_pybind.DetectorConfig()
            detector_config.model_file_path = "E:/GraduationDesign/yolov8n.trt"
            detector_config.src_width = width
            detector_config.src_height = height
            detector_config.batch_size = 1
            detector = tensorrt_alpha_pybind.Detector(detector_config)
            frames = detector.inference(np.asarray(img.copy(), dtype=np.uint8))
            if frames and len(frames) > 0:
                boxes = frames[0]
                for box in boxes:
                    xmin = box.left
                    ymin = box.top
                    w = box.right - box.left
                    h = box.bottom - box.top
                    label = box.label
                    score = box.score
                    label_text = f"cls{int(label)} conf{score:.2f}"
                    cv2.rectangle(img, (int(xmin), int(ymin)),
                                  (int(xmin + w), int(ymin + h)),
                                  (0, 255, 0), 2)
                    cv2.putText(img, label_text, (int(xmin), int(ymin) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                (0, 255, 0), 2)
        except Exception as e:
            log_strs = [str(e)]
            frames = []
        output_img_path = output_path + "_0.jpg"
        cv2.imwrite(output_img_path, img)
        with ClusterRpcProxy(config.get_rpc_config()) as cluster_rpc:
            urls = [cluster_rpc.object_storage_service.upload_object(output_img_path)]
        return {
            'urls': urls,
            'logs': log_strs,
            'frames': frames,
        }
