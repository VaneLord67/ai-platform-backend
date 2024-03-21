import json

import cv2
import socketio

from ais.yolo_hx import inference_by_yolo_detector, \
    parse_results, draw_results, init_yolo_detector_config, init_yolo_detector_by_config
from common import config
from common.camera_background_process import CameraBackgroundProcess
from common.log import LOGGER
from common.unbuffered_video_capture import UnbufferedVideoCapture
from common.util import clear_camera_temp_resource
from microservice.detection_hx import DetectionService
from scripts.camera_common import after_camera_call, parse_camera_command_args


def camera_cpp_call(camera_id, hyperparameters, namespace, task_id, service_unique_id,
                    camera_output_path, camera_output_json_path):
    try:
        stop_camera_flag = False

        LOGGER.info(f'open camera: {camera_id}')

        unbuffered_cap = UnbufferedVideoCapture(camera_id)
        frame_width, frame_height = unbuffered_cap.get_param()

        yolo_config = init_yolo_detector_config(frame_width, frame_height)
        yolo_detector = init_yolo_detector_by_config(yolo_config)

        sio = socketio.Client()

        @sio.on('connect', namespace=namespace)
        def on_connect():
            LOGGER.info('emit post_producer_id event')
            sio.emit('post_producer_id', namespace=namespace)

        @sio.on('stop_camera', namespace=namespace)
        def on_stop_camera():
            nonlocal stop_camera_flag
            LOGGER.info(f'stop camera: {camera_id}')
            stop_camera_flag = True

        sio.connect(f'http://{config.config.get("flask_host")}:{config.config.get("flask_port")}{namespace}')
        camera_background_process = CameraBackgroundProcess(camera_output_path, camera_output_json_path,
                                                          frame_width, frame_height)
        # 逐帧读取视频
        while not stop_camera_flag:
            log = unbuffered_cap.get_log()
            if log:
                sio.emit('log', log, namespace=namespace)
            # 读取一帧
            image = unbuffered_cap.read()
            if image is None:
                break
            _, jpg_data = cv2.imencode(".jpg", image)
            # 对帧进行处理
            results, input_images = inference_by_yolo_detector(yolo_detector, image)
            rects = parse_results(results)
            json_items = []
            for rect in rects:
                xmin, ymin, w, h, label, score = rect
                json_item = {
                    'xmin': xmin,
                    'ymin': ymin,
                    'w': w,
                    'h': h,
                    'label': label,
                    'score': score,
                }
                json_items.append(json_item)
            json_items_str = json.dumps(json_items)
            sio.emit('camera_data', jpg_data.tobytes(), namespace=namespace)
            sio.emit('camera_data', json_items_str, namespace=namespace)
            draw_results(input_images, results, save_path=None)
            if len(input_images) > 0:
                camera_background_process.put(image, json_items_str)

        # 释放资源
        unbuffered_cap.release()
        sio.disconnect()
        camera_background_process.release()

        after_camera_call(camera_output_path, camera_output_json_path,
                          task_id, DetectionService.name, service_unique_id)
    finally:
        clear_camera_temp_resource(camera_output_path, camera_output_json_path)


if __name__ == '__main__':
    camera_id, hps, namespace, task_id, service_unique_id, \
        camera_output_path, camera_output_json_path = parse_camera_command_args()
    camera_cpp_call(camera_id, hps, namespace, task_id, service_unique_id,
                    camera_output_path, camera_output_json_path)
