import platform
import subprocess
from enum import Enum

import numpy as np

from common.log import LOGGER

plat = platform.system().lower()


class MessageType(Enum):
    PARAMETER_TYPE = 0
    IMAGE_FRAME = 1
    SEI = 2
    END_MESSAGE = 3
    ERROR = 4


class SEIParser:
    message_type_size = 1
    parameter_type_size = 4
    sei_len_size = 4
    command = ['video/ffmpeg_sei_parse.exe' if plat == 'windows' else 'video/ffmpeg_sei_parser']

    def __init__(self, url):
        # rtsp/rtmp都可以作为url
        self.pipe = subprocess.Popen(self.command + [url], shell=False, stdout=subprocess.PIPE)
        self.width = 0
        self.height = 0
        self.url = url

    def start(self):
        """
        从进程的stdout中读取字节流，字节流中每个消息的格式为：
        message_type + message
        其中message_type占message_type_size个字节，根据message_type来决定后面读取的方式
        """
        while True:
            message_type_byte = self.pipe.stdout.read(self.message_type_size)
            message_type = int.from_bytes(message_type_byte, byteorder='little')
            if message_type == MessageType.END_MESSAGE.value:
                LOGGER.info(f"url: {self.url} ended")
                break
            elif message_type == MessageType.PARAMETER_TYPE.value:
                # 宽度和高度信息很重要，根据宽高才能知道读取帧时应该读多少个字节，即width * height * 3个字节
                width_byte = self.pipe.stdout.read(self.parameter_type_size)
                height_byte = self.pipe.stdout.read(self.parameter_type_size)
                width = int.from_bytes(width_byte, byteorder='little')
                height = int.from_bytes(height_byte, byteorder='little')
                self.width = width
                self.height = height
                yield message_type, width, height
            elif message_type == MessageType.SEI.value:
                sei_data_len_byte = self.pipe.stdout.read(self.sei_len_size)
                sei_data_len = int.from_bytes(sei_data_len_byte, byteorder='little')
                if sei_data_len <= 0:
                    LOGGER.error("sei data len error")
                    break
                sei_data = self.pipe.stdout.read(sei_data_len)
                if len(sei_data) < sei_data_len:
                    LOGGER.error("sei data error")
                    break
                yield message_type, sei_data.decode('utf-8')
            elif message_type == MessageType.IMAGE_FRAME.value:
                bgr24_data = self.pipe.stdout.read(self.height * self.width * 3)
                if len(bgr24_data) < self.height * self.width * 3:
                    LOGGER.error("bgr24 data len error")
                    break
                bgr_img = np.frombuffer(bgr24_data, dtype=np.uint8).reshape((self.height, self.width, 3))
                yield message_type, bgr_img
        if self.pipe:
            self.pipe.terminate()

    def release(self):
        LOGGER.info(f"sei parser {self.url} release")
        if self.pipe:
            self.pipe.terminate()
