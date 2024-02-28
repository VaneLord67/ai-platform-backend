import json
from datetime import timedelta

import cv2
from nameko.events import event_handler, BROADCAST

from ais import libutil_bytetrack as bytetrack_util
from ais.yolo_hx import inference, parse_results, draw_results, convert_parsed_to_yolo_rect
from common.util import create_redis_client, \
    clear_camera_temp_resource
from microservice.ai_base import AIBaseService
from microservice.manage import ManageService
from model.ai_model import AIModel
from model.service_info import ServiceInfo
from model.support_input import *


def init_state_info():
    service_info = ServiceInfo()

    model = AIModel()
    model.field = "跟踪"
    model.hyperparameters = []
    model.name = "yoloV8 + ByteTrack"
    model.support_input = [VIDEO_URL_TYPE, CAMERA_TYPE]

    service_info.model = model
    return service_info


class TrackService(AIBaseService):
    name = "track_service"

    service_info = init_state_info()

    video_script_name = "scripts/track_hx_video.py"

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
    def camera_cpp_call(camera_id, hyperparameters, stop_signal_key,
                        camera_data_queue_name, log_key, task_id, service_unique_id,
                        camera_output_path, camera_output_json_path):
        try:
            video_capture = cv2.VideoCapture(camera_id)
            # 检查视频文件是否成功打开
            if not video_capture.isOpened():
                print("Error: Unable to open video file.")
                exit()
            frame_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = 30

            tracker = bytetrack_util.ByteTrackUtil(30)
            out = cv2.VideoWriter(camera_output_path, cv2.VideoWriter_fourcc(*'avc1'), fps, (frame_width, frame_height))
            redis_client = create_redis_client()
            redis_client.expire(camera_data_queue_name, time=timedelta(seconds=60))
            with open(camera_output_json_path, 'w') as f:
                # 逐帧读取视频
                while True:
                    key_count = redis_client.exists(stop_signal_key)
                    if key_count > 0:
                        redis_client.rpush(camera_data_queue_name, "stop")
                        redis_client.expire(camera_data_queue_name, time=timedelta(seconds=60))
                        break

                    # 读取一帧
                    ret, image = video_capture.read()
                    # 检查是否成功读取帧
                    if not ret:
                        break
                    # 对帧进行处理
                    results, input_images = inference(image)
                    rects = parse_results(results)

                    yolo_rects = convert_parsed_to_yolo_rect(rects)
                    yolo_rects = tracker.update(yolo_rects)
                    json_items = []
                    for yolo_rect in yolo_rects:
                        json_item = {
                            'xmin': yolo_rect.xmin,
                            'ymin': yolo_rect.ymin,
                            'w': yolo_rect.w,
                            'h': yolo_rect.h,
                            'label': yolo_rect.label,
                            'score': yolo_rect.score,
                            'track_id': yolo_rect.track_id,
                        }
                        json_items.append(json_item)
                    json_items_str = json.dumps(json_items)
                    redis_client.rpush(camera_data_queue_name, json_items_str)
                    f.write(json_items_str + '\n')
                    draw_results(input_images, results, save_path=None)
                    if len(input_images) > 0:
                        out.write(input_images[0])
                        _, jpg_data = cv2.imencode(".jpg", input_images[0])
                        jpg_bytes = jpg_data.tobytes()
                        redis_client.rpush(camera_data_queue_name, jpg_bytes)

                # 释放资源
                video_capture.release()
                out.release()
                cv2.destroyAllWindows()

            AIBaseService.after_camera_call(camera_output_path, camera_output_json_path,
                                            task_id, TrackService.name, service_unique_id)
        finally:
            clear_camera_temp_resource(camera_output_path, camera_output_json_path)
