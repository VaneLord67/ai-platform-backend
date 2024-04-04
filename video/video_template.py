import json
from datetime import timedelta

import cv2

from common.log import LOGGER
from common.util import create_redis_client
from scripts.video_common import after_video_call
from video.background_write_process import BackgroundWriteProcess


class VideoTemplate:
    def __init__(self, video_path, video_output_path, video_output_json_path, video_progress_key,
                 hyperparameters, task_id, service_unique_id, service_name, ai_func=None):
        # ai_func接收image返回以字典为元素的列表
        self.ai_func = ai_func
        self.task_id = task_id
        self.log_key = task_id + "_log"
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
        self.width = frame_width
        self.height = frame_height
        fps = int(video_capture.get(cv2.CAP_PROP_FPS))
        self.camera_write_process = BackgroundWriteProcess(self.video_output_path, self.video_output_json_path,
                                                           self.width, self.height, fps)
        self.total_frame_count = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_capture = video_capture
        self.redis_client = create_redis_client()
        self.redis_client.setex(name=video_progress_key, time=timedelta(days=1), value="0.00")

    def loop_process(self):
        try:
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
                    self.camera_write_process.put(image, json.dumps(json_items))
        except Exception as e:
            self.log(str(e))
            raise
        finally:
            self.video_capture.release()
            self.camera_write_process.release()
            after_video_call(self.video_output_path, self.video_output_json_path,
                             self.task_id, self.service_name, self.service_unique_id)

    def log(self, log_str):
        pipeline = self.redis_client.pipeline()
        pipeline.rpush(self.log_key, log_str)
        pipeline.expire(self.log_key, timedelta(days=1))
        pipeline.execute()
