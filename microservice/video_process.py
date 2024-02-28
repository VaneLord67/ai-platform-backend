import json
import sys
from datetime import timedelta

import cv2
from nameko.standalone.rpc import ClusterRpcProxy

from ais.yolo_hx import init_yolo_detector_config, init_yolo_detector_by_config, inference_by_yolo_detector, \
    parse_results, draw_results
from common.config import config
from common.log import LOGGER
from common.util import create_redis_client, clear_video_temp_resource
from microservice.mqtt_storage import MQTTStorage
from model.hyperparameter import Hyperparameter


def after_video_call(video_output_path, video_output_json_path, task_id, service_name, service_unique_id):
    """
    由于多进程进行传参时，无法将rpc对象以及redis client对象进行传递，所以只能重新创建对象来进行服务调用。
    如果你有更好的方法，可以将其改进。
    """
    with ClusterRpcProxy(config.get_rpc_config()) as cluster_rpc:
        video_url = cluster_rpc.object_storage_service.upload_object(video_output_path)
        json_url = cluster_rpc.object_storage_service.upload_object(video_output_json_path)
        client = create_redis_client()
        mapping = {
            "video_url": video_url,
            "json_url": json_url,
        }
        client.hset(name=task_id, mapping=mapping)
        client.expire(name=task_id, time=timedelta(hours=24))
        mqtt_storage = MQTTStorage()
        mqtt_storage.setup()
        msg = {
            'task_id': task_id,
            'video_url': video_url,
            'json_url': json_url,
        }
        mqtt_storage.push_message(json.dumps(msg))
        mqtt_storage.client.loop(timeout=1)
        cluster_rpc.manage_service.change_state_to_ready(service_name, service_unique_id)
        LOGGER.info(f"video task done, task_id:{task_id}")


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

        # 配置文件参数定义
        yolo_config = init_yolo_detector_config(frame_width, frame_height)
        yolo_detector = init_yolo_detector_by_config(yolo_config)

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
                f.write(json.dumps(json_items) + '\n')
                draw_results(input_images, results, save_path=None)
                if len(input_images) > 0:
                    out.write(input_images[0])

            # 释放资源
            video_capture.release()
            out.release()

            after_video_call(video_output_path, video_output_json_path,
                             task_id, "detection_service", service_unique_id)
    finally:
        clear_video_temp_resource(video_path, video_output_path, video_output_json_path)


if __name__ == '__main__':
    '''
    video_path, video_output_path, video_output_json_path, video_progress_key,
                   hyperparameters, task_id, service_unique_id'''
    # 获取命令行参数
    args = sys.argv[1:]
    print("Received arguments:", args)
    if len(args) != 7:
        raise ValueError('args length error')
    video_path, video_output_path, video_output_json_path, video_progress_key, \
        hyperparameters_json_str, task_id, service_unique_id = args
    hp_dict_list = json.loads(hyperparameters_json_str)
    hps = []
    for hp_dict in hp_dict_list:
        hp = Hyperparameter().from_dict(hp_dict)
        hps.append(hp)
    video_cpp_call(video_path, video_output_path, video_output_json_path, video_progress_key,
                   hps, task_id, service_unique_id)
