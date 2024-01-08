import base64
import json
from typing import Union

import cv2
import numpy as np
import redis

from common.config import config
from common.util import create_redis_client
from model.box import Box


def show_result(client, queue_name):
    print("start get data from queue................")
    state = 0
    _, queue_data = client.blpop([queue_name])
    while queue_data:
        # print(f"queue_data = {queue_data}")
        if queue_data == b'stop':
            break
        if state == 0:
            jpg_as_text = base64.b64encode(queue_data).decode('utf-8')
            print(f"jpg_base64 = {jpg_as_text}")
            # 将字节序列解码为numpy数组
            image_np = np.frombuffer(queue_data, dtype=np.uint8)
            # 使用OpenCV解码图像
            image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
            # 展示图像
            state = 1
            # print(f"image_np = {image_np}")
            cv2.imshow('Image from Redis', image)
            cv2.waitKey(1)
        elif state == 1:
            cppBoxes = json.loads(queue_data)
            for cppBox in cppBoxes:
                box = Box(cppBox['left'], cppBox['right'], cppBox['bottom'], cppBox['top'], cppBox['confidence'],
                          cppBox['label'])
                # print(f"box = {box}")
            state = 0
        _, queue_data = client.blpop([queue_name])
    cv2.destroyAllWindows()


if __name__ == '__main__':
    queue_name = "my_queue"
    stopSignalKey = "stop"
    client = create_redis_client()
    show_result(client, queue_name)
