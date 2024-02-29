import json
from datetime import timedelta

import cv2

from ais import libutil_bytetrack as bytetrack_util
from ais.yolo_hx import init_yolo_detector_config, init_yolo_detector_by_config, inference_by_yolo_detector, \
    parse_results, convert_parsed_to_yolo_rect, draw_track_results
from common.util import create_redis_client, clear_video_temp_resource
from scripts.video_common import after_video_call, parse_video_command_args


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

        yolo_config = init_yolo_detector_config(frame_width, frame_height)
        yolo_detector = init_yolo_detector_by_config(yolo_config)

        fps = int(video_capture.get(cv2.CAP_PROP_FPS))
        current_frame_count = 0

        tracker = bytetrack_util.ByteTrackUtil(30)
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
                f.write(json.dumps(json_items) + '\n')
                draw_track_results(input_images, yolo_rects, save_path=None)
                if len(input_images) > 0:
                    out.write(input_images[0])

            # 释放资源
            video_capture.release()
            out.release()

            after_video_call(video_output_path, video_output_json_path,
                             task_id, "track_service", service_unique_id)
    finally:
        clear_video_temp_resource(video_path, video_output_path, video_output_json_path)


if __name__ == '__main__':
    video_path, video_output_path, video_output_json_path, video_progress_key, \
        hps, task_id, service_unique_id = parse_video_command_args()
    video_cpp_call(video_path, video_output_path, video_output_json_path, video_progress_key,
                   hps, task_id, service_unique_id)
