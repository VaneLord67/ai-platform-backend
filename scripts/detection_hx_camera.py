import json

import cv2
import socketio

from ais.yolo_hx import inference_by_yolo_detector, \
    parse_results, draw_results, init_yolo_detector_config, init_yolo_detector_by_config
from common import config
from common.log import LOGGER
from common.unbuffered_video_capture import UnbufferedVideoCapture
from common.util import clear_camera_temp_resource
from microservice.detection_hx import DetectionService
from scripts.camera_common import after_camera_call, parse_camera_command_args


def camera_cpp_call(camera_id, hyperparameters, namespace, task_id, service_unique_id,
                    camera_output_path, camera_output_json_path):
    try:
        emit_data = None
        stop_camera_flag = False
        sio = socketio.Client()
        sio.connect(f'http://{config.config.get("flask_host")}:{config.config.get("flask_port")}{namespace}')

        @sio.on('connect', namespace=namespace)
        def on_connect():
            sio.emit('post_producer_id', namespace=namespace)

        @sio.on('camera_retrieve', namespace=namespace)
        def on_camera_retrieve():
            if emit_data is None:
                LOGGER.error("emit_data empty")
                return
            if len(emit_data) != 2:
                LOGGER.error("emit_data length error")
                return
            sio.emit('camera_data', emit_data[0].tobytes(), namespace=namespace)
            sio.emit('camera_data', emit_data[1], namespace=namespace)

        @sio.on('stop_camera', namespace=namespace)
        def on_stop_camera():
            nonlocal stop_camera_flag
            LOGGER.info(f'stop camera: {camera_id}')
            stop_camera_flag = True

        LOGGER.info(f'open camera: {camera_id}')
        video_capture = cv2.VideoCapture(camera_id)
        # 检查视频文件是否成功打开
        if not video_capture.isOpened():
            LOGGER.error("Error: Unable to open camera.")
            return
        frame_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        LOGGER.info(f'camera size: {frame_width}x{frame_height}')

        yolo_config = init_yolo_detector_config(frame_width, frame_height)
        yolo_detector = init_yolo_detector_by_config(yolo_config)

        unbuffered_cap = UnbufferedVideoCapture(camera_id)

        fps = 30
        out = cv2.VideoWriter(camera_output_path, cv2.VideoWriter_fourcc(*'avc1'), fps, (frame_width, frame_height))
        with open(camera_output_json_path, 'w') as f:
            # 逐帧读取视频
            while not stop_camera_flag:
                # 读取一帧
                image = unbuffered_cap.read()
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
                emit_data = (jpg_data, json_items_str)
                f.write(json_items_str + '\n')
                draw_results(input_images, results, save_path=None)
                if len(input_images) > 0:
                    out.write(input_images[0])

        # 释放资源
        video_capture.release()
        unbuffered_cap.release()
        out.release()
        sio.disconnect()

        after_camera_call(camera_output_path, camera_output_json_path,
                          task_id, DetectionService.name, service_unique_id)
    finally:
        clear_camera_temp_resource(camera_output_path, camera_output_json_path)


if __name__ == '__main__':
    camera_id, hps, namespace, task_id, service_unique_id, \
        camera_output_path, camera_output_json_path = parse_camera_command_args()
    camera_cpp_call(camera_id, hps, namespace, task_id, service_unique_id,
                    camera_output_path, camera_output_json_path)
