import cv2
import numpy as np

from ais import util_bytetrack, tensorrt_alpha_pybind
from common.util import clear_camera_temp_resource
from microservice.recognition import RecognitionService
from scripts.camera_common import parse_camera_command_args
from video.camera_template import CameraTemplate


def camera_cpp_call(camera_id, hyperparameters, namespace, task_id, service_unique_id,
                    camera_output_path, camera_output_json_path):
    try:

        camera_template = CameraTemplate(camera_id, hyperparameters, namespace, task_id, service_unique_id,
                                         camera_output_path, camera_output_json_path, RecognitionService.name)

        detector_config = tensorrt_alpha_pybind.DetectorConfig()
        detector_config.model_file_path = "E:/GraduationDesign/yolov8n.trt"
        detector_config.src_width = camera_template.width
        detector_config.src_height = camera_template.height
        detector_config.batch_size = 1
        detector = tensorrt_alpha_pybind.Detector(detector_config)
        bytetrack_util = util_bytetrack.ByteTrackUtil(30)

        def ai_func(image):
            frame_boxes = detector.inference(np.asarray(image.copy(), dtype=np.uint8))
            json_items = []
            if frame_boxes and len(frame_boxes) > 0:
                boxes = frame_boxes[0]
                bytetrack_rects = []
                for box in boxes:
                    xmin = box.left
                    ymin = box.top
                    w = box.right - box.left
                    h = box.bottom - box.top
                    label = box.label
                    score = box.confidence

                    bytetrack_rect = util_bytetrack.ByteTrackUtilYoloRect()
                    bytetrack_rect.xmin = xmin
                    bytetrack_rect.ymin = ymin
                    bytetrack_rect.w = w
                    bytetrack_rect.h = h
                    bytetrack_rect.label = int(label)
                    bytetrack_rect.score = score

                    bytetrack_rects.append(bytetrack_rect)
                bytetrack_rects = bytetrack_util.update(bytetrack_rects)
                for bytetrack_rect in bytetrack_rects:
                    xmin = bytetrack_rect.xmin
                    ymin = bytetrack_rect.ymin
                    w = bytetrack_rect.w
                    h = bytetrack_rect.h
                    label = bytetrack_rect.label
                    score = bytetrack_rect.score
                    track_id = bytetrack_rect.track_id

                    label_text = f"cls{int(label)} conf{score:.2f} track_id{track_id}"
                    cv2.rectangle(image, (int(xmin), int(ymin)),
                                  (int(xmin + w), int(ymin + h)),
                                  (0, 255, 0), 2)
                    cv2.putText(image, label_text, (int(xmin), int(ymin) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                (0, 255, 0), 2)
                    json_item = {
                        'xmin': xmin,
                        'ymin': ymin,
                        'w': w,
                        'h': h,
                        'label': label,
                        'score': score,
                        'track_id': track_id,
                    }
                    json_items.append(json_item)
            return json_items

        camera_template.ai_func = ai_func
        camera_template.loop_process()
    finally:
        clear_camera_temp_resource(camera_output_path, camera_output_json_path)


if __name__ == '__main__':
    camera_args = parse_camera_command_args()
    camera_cpp_call(*camera_args)
