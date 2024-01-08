import base64
import json
from typing import Union

import cv2
import numpy as np
import redis

from common.config import config
from common.util import create_redis_client
from model.box import Box
from model.cls_result import ClsResult


def show_result(client, queue_name):
    print("start get data from queue................")
    _, queue_data = client.blpop([queue_name])
    while queue_data:
        # print(f"queue_data = {queue_data}")
        if queue_data == b'stop':
            break
        if queue_data[:len(b'{')] != b'{':
            # jpg_as_text = base64.b64encode(queue_data).decode('utf-8')
            # print(f"jpg_base64 = {jpg_as_text}")
            # 将字节序列解码为numpy数组
            image_np = np.frombuffer(queue_data, dtype=np.uint8)
            # 使用OpenCV解码图像
            image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
            # 展示图像
            # print(f"image_np = {image_np}")
            cv2.imshow('Image from Redis', image)
            cv2.waitKey(1)
        else:
            # cppClsResult = json.loads(queue_data)
            # clsResult = ClsResult(cppClsResult.label, cppClsResult.class_name, cppClsResult.confidence)
            clsResult = ClsResult().from_json(queue_data)
            print(f"result = {clsResult}")
        _, queue_data = client.blpop([queue_name])
    cv2.destroyAllWindows()


if __name__ == '__main__':
    queue_name = "my_queue"
    stopSignalKey = "stop"
    client = create_redis_client()
    show_result(client, queue_name)
