import json
from datetime import timedelta

import cv2
import numpy as np

from common.log import LOGGER
from common.util import create_redis_client, clear_video_temp_resource
from microservice.detection_hx import DetectionService
from scripts.video_common import after_video_call, parse_video_command_args
from ais import tensorrt_alpha_pybind


def video_cpp_call(video_path, video_output_path, video_output_json_path, video_progress_key,
                   hyperparameters, task_id, service_unique_id):
    try:
        video_capture = cv2.VideoCapture(video_path)
        # 检查视频文件是否成功打开
        if not video_capture.isOpened():
            LOGGER.error("Error: Unable to open video file.")
            return
        frame_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        LOGGER.info(f'video size = {frame_width}x{frame_height}')
        total_frame_count = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))

        detector_config = tensorrt_alpha_pybind.DetectorConfig()
        detector_config.model_file_path = "E:/GraduationDesign/yolov8n.trt"
        detector_config.src_width = frame_width
        detector_config.src_height = frame_height
        detector_config.batch_size = 1
        detector = tensorrt_alpha_pybind.Detector(detector_config)

        fps = int(video_capture.get(cv2.CAP_PROP_FPS))
        current_frame_count = 0

        out = cv2.VideoWriter(video_output_path, cv2.VideoWriter_fourcc(*'avc1'), fps, (frame_width, frame_height))
        redis_client = create_redis_client()
        redis_client.setex(name=video_progress_key, time=timedelta(days=1), value="0.00")
        with open(video_output_json_path, 'w') as f:
            # 逐帧读取视频
            while True:
                # 读取一帧
                ret, image = video_capture.read()
                # 检查是否成功读取帧
                if not ret:
                    break
                current_frame_count += 1
                progress_str = "%.2f" % (current_frame_count / total_frame_count)
                redis_client.setex(name=video_progress_key, time=timedelta(days=1), value=progress_str)
                # 对帧进行处理
                frame_boxes = detector.inference(np.asarray(image.copy(), dtype=np.uint8))
                json_items = []
                if frame_boxes and len(frame_boxes) > 0:
                    boxes = frame_boxes[0]
                    for box in boxes:
                        xmin = box.left
                        ymin = box.top
                        w = box.right - box.left
                        h = box.bottom - box.top
                        label = box.label
                        score = box.confidence
                        label_text = f"cls{int(label)} conf{score:.2f}"
                        cv2.rectangle(image, (int(xmin), int(ymin)),
                                      (int(xmin + w), int(ymin + h)),
                                      (0, 255, 0), 2)
                        cv2.putText(image, label_text, (int(xmin), int(ymin) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                    (0, 255, 0), 2)
                        json_item = {
                            'xmin': box.left,
                            'ymin': box.top,
                            'w': box.right - box.left,
                            'h': box.bottom - box.top,
                            'label': box.label,
                            'score': box.confidence,
                        }
                        json_items.append(json_item)
                f.write(json.dumps(json_items) + '\n')
                out.write(image)

            # 释放资源
            video_capture.release()
            out.release()

            after_video_call(video_output_path, video_output_json_path,
                             task_id, DetectionService.name, service_unique_id)
    finally:
        clear_video_temp_resource(video_path, video_output_path, video_output_json_path)


if __name__ == '__main__':
    video_path, video_output_path, video_output_json_path, video_progress_key, \
        hps, task_id, service_unique_id = parse_video_command_args()
    video_cpp_call(video_path, video_output_path, video_output_json_path, video_progress_key,
                   hps, task_id, service_unique_id)
