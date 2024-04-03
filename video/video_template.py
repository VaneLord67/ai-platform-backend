import json
from datetime import timedelta

import cv2

from common.log import LOGGER
from common.util import create_redis_client
from scripts.video_common import after_video_call


class VideoTemplate:
    def __init__(self, video_path, video_output_path, video_output_json_path, video_progress_key,
                 hyperparameters, task_id, service_unique_id, service_name, ai_func):
        self.ai_func = ai_func
        self.task_id = task_id
        self.service_unique_id = service_unique_id
        self.video_path = video_path
        self.video_output_path = video_output_path
        self.video_output_json_path = video_output_json_path
        self.video_progress_key = video_progress_key
        self.service_name = service_name
        video_capture = cv2.VideoCapture(video_path)
        # 检查视频文件是否成功打开
        if not video_capture.isOpened():
            LOGGER.error(f"Error: Unable to open video file: {video_path}")
            return
        frame_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        LOGGER.info(f'video size = {frame_width}x{frame_height}')
        self.total_frame_count = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = int(video_capture.get(cv2.CAP_PROP_FPS))
        self.video_capture = video_capture
        self.out = cv2.VideoWriter(video_output_path, cv2.VideoWriter_fourcc(*'avc1'), fps, (frame_width, frame_height))
        self.redis_client = create_redis_client()
        self.redis_client.setex(name=video_progress_key, time=timedelta(days=1), value="0.00")

    def loop_process(self):
        current_frame_count = 0
        with open(self.video_output_json_path, 'w') as f:
            # 逐帧读取视频
            while True:
                # 读取一帧
                ret, image = self.video_capture.read()
                # 检查是否成功读取帧
                if not ret:
                    break
                current_frame_count += 1
                progress_str = "%.2f" % (current_frame_count / self.total_frame_count)
                self.redis_client.setex(name=self.video_progress_key, time=timedelta(days=1), value=progress_str)
                # 对帧进行处理
                json_items = self.ai_func(image)
                f.write(json.dumps(json_items) + '\n')
                self.out.write(image)
        # 释放资源
        self.video_capture.release()
        self.out.release()
        after_video_call(self.video_output_path, self.video_output_json_path,
                         self.task_id, self.service_name, self.service_unique_id)
