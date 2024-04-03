import json
from datetime import timedelta

import cv2

from ais.yolo_hx import parse_results, draw_results, init_yolo_detector_config, init_yolo_detector_by_config, \
    inference_by_yolo_detector, convert_parsed_to_yolo_rect
from ais import libutil_bytetrack as bytetrack_util
from video.unbuffered_video_capture import UnbufferedVideoCapture
from common.util import create_redis_client, clear_camera_temp_resource
from microservice.track_hx import TrackService
from scripts.camera_common import parse_camera_command_args, after_camera_call


def camera_cpp_call(camera_id, hyperparameters, stop_signal_key,
                    camera_data_queue_name, log_key, task_id, service_unique_id,
                    camera_output_path, camera_output_json_path):
    try:
        video_capture = cv2.VideoCapture(camera_id)
        # 检查视频文件是否成功打开
        if not video_capture.isOpened():
            print("Error: Unable to open video file.")
            exit()
        unbuffered_cap = UnbufferedVideoCapture(camera_id)
        frame_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = 30

        tracker = bytetrack_util.ByteTrackUtil(30)
        yolo_config = init_yolo_detector_config(frame_width, frame_height)
        yolo_detector = init_yolo_detector_by_config(yolo_config)
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
                image = unbuffered_cap.read()
                # 对帧进行处理
                results, input_images = inference_by_yolo_detector(yolo_detector, image)
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

        after_camera_call(camera_output_path, camera_output_json_path,
                          task_id, TrackService.name, service_unique_id)
    finally:
        clear_camera_temp_resource(camera_output_path, camera_output_json_path)


if __name__ == '__main__':
    camera_id, hps, stop_signal_key, \
        camera_data_queue_name, log_key, task_id, service_unique_id, \
        camera_output_path, camera_output_json_path = parse_camera_command_args()
    camera_cpp_call(camera_id, hps, stop_signal_key,
                    camera_data_queue_name, log_key, task_id, service_unique_id,
                    camera_output_path, camera_output_json_path)
