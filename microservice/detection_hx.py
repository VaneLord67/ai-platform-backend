import json
from datetime import timedelta

import cv2
from nameko.events import event_handler, BROADCAST
from nameko.standalone.rpc import ClusterRpcProxy

from ais.yolo_hx import inference, parse_results, draw_results, parsed_to_json
from common import config
from common.util import clear_video_temp_resource, create_redis_client, \
    clear_camera_temp_resource
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
                    frames = parse_results(results)
                    json_items = []
                    if len(frames) > 0:
                        this_frame = frames[0]
                        for rect in this_frame:
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
                                            task_id, DetectionService.name, service_unique_id)
        finally:
            clear_camera_temp_resource(camera_output_path, camera_output_json_path)

    @staticmethod
    def video_cpp_call(video_path, video_output_path, video_output_json_path, video_progress_key,
                       hyperparameters, task_id, service_unique_id):
        try:
            video_capture = cv2.VideoCapture(video_path)
            # 检查视频文件是否成功打开
            if not video_capture.isOpened():
                print("Error: Unable to open video file.")
                exit()
            frame_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frame_count = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = int(video_capture.get(cv2.CAP_PROP_FPS))
            current_frame_count = 0

            out = cv2.VideoWriter(video_output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (frame_width, frame_height))
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
                    results, input_images = inference(image)

                    frames = parse_results(results)
                    json_items = []
                    if len(frames) > 0:
                        this_frame = frames[0]
                        for rect in this_frame:
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
                    f.write(json.dumps(json_items) + '\n')
                    draw_results(input_images, results, save_path=None)
                    if len(input_images) > 0:
                        out.write(input_images[0])

                # 释放资源
                video_capture.release()
                out.release()
                cv2.destroyAllWindows()

                AIBaseService.after_video_call(video_output_path, video_output_json_path,
                                               task_id, DetectionService.name, service_unique_id)
        finally:
            clear_video_temp_resource(video_path, video_output_path, video_output_json_path)

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
