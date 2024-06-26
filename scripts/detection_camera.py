import json
import subprocess
import time

import cv2
import numpy as np
import socketio

from ais import tensorrt_alpha_pybind
from common import config
from microservice.detection import DetectionService
from video.background_write_process import BackgroundWriteProcess
from common.log import LOGGER
from common.util import clear_camera_temp_resource
from scripts.camera_common import after_camera_call, parse_camera_command_args
from video.camera_mode_enum import CameraModeEnum
from video.sei_injector import SEIInjector
from video.unbuffered_sei_parser import UnbufferedSEIParser


def camera_cpp_call(camera_id, hyperparameters, namespace, task_id, service_unique_id,
                    camera_output_path, camera_output_json_path):
    try:
        stop_camera_flag = False
        LOGGER.info(f'open camera: {camera_id}')

        camera_mode = CameraModeEnum.WEBRTC_STREAMER.value
        for hyperparameter in hyperparameters:
            if hyperparameter.name == 'camera_mode':
                camera_mode = hyperparameter.value
                break
        LOGGER.info(f'camera_mode: {camera_mode}')

        diff_timestamp = 0
        sei_injector = None
        pipe = None
        if camera_mode == CameraModeEnum.SEI.value:
            rtmp_url = f"rtmp://127.0.0.1/live{namespace}"
            sei_injector = SEIInjector(camera_id, rtmp_url)
            unbuffered_sei_parser = UnbufferedSEIParser(rtmp_url)
            width, height = unbuffered_sei_parser.get_param()
        elif camera_mode == CameraModeEnum.WEBRTC_STREAMER.value:
            unbuffered_sei_parser = UnbufferedSEIParser(camera_id)
            width, height = unbuffered_sei_parser.get_param()
        else:
            unbuffered_sei_parser = UnbufferedSEIParser(camera_id)
            width, height = unbuffered_sei_parser.get_param()
            rtmp_url = f"rtmp://127.0.0.1/live{namespace}"
            command = ['ffmpeg',
                       '-y', '-an',
                       '-f', 'rawvideo',
                       '-vcodec', 'rawvideo',
                       '-pix_fmt', 'bgr24',
                       '-s', str(width) + 'x' + str(height),
                       '-i', '-',
                       '-c:v', 'libx264',
                       '-pix_fmt', 'yuv420p',
                       '-preset', 'ultrafast',
                       '-tune', 'zerolatency',
                       '-f', 'flv',
                       rtmp_url]
            pipe = subprocess.Popen(command
                                    , shell=False
                                    , stdin=subprocess.PIPE
                                    )
        LOGGER.info(f"width: {width}, height: {height}")

        detector_config = tensorrt_alpha_pybind.DetectorConfig()
        detector_config.model_file_path = "E:/GraduationDesign/yolov8n.trt"
        detector_config.src_width = width
        detector_config.src_height = height
        detector_config.batch_size = 1
        detector = tensorrt_alpha_pybind.Detector(detector_config)

        sio = socketio.Client()

        @sio.on('connect', namespace=namespace)
        def on_connect():
            LOGGER.info('emit post_producer_id event')
            sio.emit('post_producer_id', namespace=namespace)

        @sio.on('disconnect', namespace=namespace)
        def on_disconnect():
            nonlocal stop_camera_flag
            if not stop_camera_flag:
                LOGGER.info(f'passive stop camera: {camera_id}')
                stop_camera_flag = True

        @sio.on('stop_camera', namespace=namespace)
        def on_stop_camera():
            nonlocal stop_camera_flag
            if not stop_camera_flag:
                LOGGER.info(f'active stop camera: {camera_id}')
                stop_camera_flag = True

        sio.connect(f'http://{config.config.get("flask_host")}:{config.config.get("flask_port")}{namespace}')
        background_write_process = BackgroundWriteProcess(camera_output_path, camera_output_json_path,
                                                          width, height)

        while not stop_camera_flag:
            if camera_mode == CameraModeEnum.SEI.value:
                sei_str = unbuffered_sei_parser.get_sei()
                if sei_str:
                    latest_sei_milli_timestamp = int(sei_str)
                    local_milli_timestamp = time.time() * 1000
                    diff_timestamp = local_milli_timestamp - latest_sei_milli_timestamp
            image = unbuffered_sei_parser.read()
            if image is None:
                break
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
            if camera_mode == CameraModeEnum.PYTHON_PUBLISH_STREAM.value:
                pipe.stdin.write(image.tostring())
            if camera_mode == CameraModeEnum.SEI.value:
                camera_data = {
                    'data': json_items,
                    'timestamp': int(time.time() * 1000) - diff_timestamp
                }
                json_items_str = json.dumps(camera_data)
            elif camera_mode == CameraModeEnum.WEBRTC_STREAMER.value:
                camera_data = {
                    'data': json_items,
                    'timestamp': int(time.time() * 1000)
                }
                json_items_str = json.dumps(camera_data)
            else:
                json_items_str = json.dumps(json_items)
            sio.emit('camera_data', json_items_str, namespace=namespace)
            background_write_process.put(image, json_items_str)

        # 释放资源
        sio.disconnect()
        background_write_process.release()
        unbuffered_sei_parser.release()
        if camera_mode == CameraModeEnum.PYTHON_PUBLISH_STREAM.value:
            pipe.terminate()
        if camera_mode == CameraModeEnum.SEI.value and sei_injector:
            sei_injector.release()

        after_camera_call(camera_output_path, camera_output_json_path,
                          task_id, DetectionService.name, service_unique_id)
    finally:
        clear_camera_temp_resource(camera_output_path, camera_output_json_path)


if __name__ == '__main__':
    camera_args = parse_camera_command_args()
    camera_cpp_call(*camera_args)
