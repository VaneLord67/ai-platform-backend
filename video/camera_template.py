import json
import subprocess
import time

import socketio

from common import config
from video.background_write_process import BackgroundWriteProcess
from common.log import LOGGER
from scripts.camera_common import after_camera_call
from video.camera_mode_enum import CameraModeEnum
from video.sei_injector import SEIInjector
from video.unbuffered_sei_parser import UnbufferedSEIParser


class CameraTemplate:
    def __init__(self, camera_id, hyperparameters, namespace, task_id, service_unique_id,
                 camera_output_path, camera_output_json_path, service_name, ai_func=None):
        # ai_func接收image返回以字典为元素的列表
        self.ai_func = ai_func
        self.namespace = namespace
        self.task_id = task_id
        self.service_unique_id = service_unique_id
        self.camera_output_path = camera_output_path
        self.camera_output_json_path = camera_output_json_path
        self.service_name = service_name
        self.stop_camera_flag = False
        self.camera_mode = CameraModeEnum.WEBRTC_STREAMER.value
        self.diff_timestamp = 0
        self.sei_injector = None
        self.pipe = None
        self.parse_camera_mode(hyperparameters)
        self.width = 0
        self.height = 0
        if self.camera_mode == CameraModeEnum.SEI.value:
            rtmp_url = f"rtmp://127.0.0.1/live{namespace}"
            self.sei_injector = SEIInjector(camera_id, rtmp_url)
            self.unbuffered_sei_parser = UnbufferedSEIParser(rtmp_url)
            self.width, self.height = self.unbuffered_sei_parser.get_param()
        elif self.camera_mode == CameraModeEnum.WEBRTC_STREAMER.value:
            self.unbuffered_sei_parser = UnbufferedSEIParser(camera_id)
            self.width, self.height = self.unbuffered_sei_parser.get_param()
        else:
            self.unbuffered_sei_parser = UnbufferedSEIParser(camera_id)
            self.width, self.height = self.unbuffered_sei_parser.get_param()
            rtmp_url = f"rtmp://127.0.0.1/live{namespace}"
            command = ['ffmpeg',
                       '-y', '-an',
                       '-f', 'rawvideo',
                       '-vcodec', 'rawvideo',
                       '-pix_fmt', 'bgr24',
                       '-s', str(self.width) + 'x' + str(self.height),
                       '-i', '-',
                       '-c:v', 'libx264',
                       '-pix_fmt', 'yuv420p',
                       '-preset', 'ultrafast',
                       '-tune', 'zerolatency',
                       '-f', 'flv',
                       rtmp_url]
            self.pipe = subprocess.Popen(command, shell=False, stdin=subprocess.PIPE)
        sio = socketio.Client()
        self.sio = sio

        @sio.on('disconnect', namespace=namespace)
        def on_disconnect():
            if not self.stop_camera_flag:
                LOGGER.info(f'passive stop camera: {camera_id}')
                self.stop_camera_flag = True

        @sio.on('stop_camera', namespace=namespace)
        def on_stop_camera():
            if not self.stop_camera_flag:
                LOGGER.info(f'active stop camera: {camera_id}')
                self.stop_camera_flag = True

        sio.connect(f'http://{config.config.get("flask_host")}:{config.config.get("flask_port")}{namespace}')
        self.background_write_process = BackgroundWriteProcess(camera_output_path, camera_output_json_path,
                                                                self.width, self.height)

    def loop_process(self):
        while not self.stop_camera_flag:
            if self.camera_mode == CameraModeEnum.SEI.value:
                sei_str = self.unbuffered_sei_parser.get_sei()
                if sei_str:
                    latest_sei_milli_timestamp = int(sei_str)
                    local_milli_timestamp = time.time() * 1000
                    self.diff_timestamp = local_milli_timestamp - latest_sei_milli_timestamp
            image = self.unbuffered_sei_parser.read()
            if image is None:
                break
            # 对帧进行处理
            json_items = self.ai_func(image)
            if self.camera_mode == CameraModeEnum.PYTHON_PUBLISH_STREAM.value:
                self.pipe.stdin.write(image.tostring())
            if self.camera_mode == CameraModeEnum.SEI.value:
                camera_data = {
                    'data': json_items,
                    'timestamp': int(time.time() * 1000) - self.diff_timestamp
                }
                json_items_str = json.dumps(camera_data)
            elif self.camera_mode == CameraModeEnum.WEBRTC_STREAMER.value:
                camera_data = {
                    'data': json_items,
                    'timestamp': int(time.time() * 1000)
                }
                json_items_str = json.dumps(camera_data)
            else:
                json_items_str = json.dumps(json_items)
            self.sio.emit('camera_data', json_items_str, namespace=self.namespace)
            self.background_write_process.put(image, json_items_str)
        self.sio.disconnect()
        self.background_write_process.release()
        self.unbuffered_sei_parser.release()
        if self.camera_mode == CameraModeEnum.PYTHON_PUBLISH_STREAM.value:
            self.pipe.terminate()
        if self.camera_mode == CameraModeEnum.SEI.value and self.sei_injector:
            self.sei_injector.release()
        after_camera_call(self.camera_output_path, self.camera_output_json_path,
                          self.task_id, self.service_name, self.service_unique_id)

    def parse_camera_mode(self, hyperparameters):
        for hyperparameter in hyperparameters:
            if hyperparameter.name == 'camera_mode':
                self.camera_mode = hyperparameter.value
                return

    def log(self, log_str):
        self.sio.emit('log', log_str, namespace=self.namespace)
