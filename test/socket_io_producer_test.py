import random

import cv2
import socketio


def main():
    # 创建 Socket.IO 客户端
    sio = socketio.Client()
    stop_camera_flag = False

    # 定义连接 Namespace 的处理函数
    @sio.on('connect', namespace='/test')
    def on_connect():
        print('Connected to /test Namespace!')
        sio.emit('post_producer_id', namespace='/test')

    @sio.on('stop_camera', namespace='/test')
    def on_stop_camera():
        print('Received stop_camera event!')
        sio.disconnect()
        nonlocal stop_camera_flag
        stop_camera_flag = True

    @sio.on('camera_retrieve', namespace='/test')
    def on_camera_retrieve():
        print('Received camera_retrieve event!')
        sio.emit('camera_data', jpg_data.tobytes(), namespace='/test')

    # 启动客户端
    sio.connect('http://localhost:8086/test')  # 修改为服务器地址和 Namespace 名称

    # sio.wait()
    while not stop_camera_flag:
        # img = cv2.imread(random.choice(["test/bus.jpg", "test/zidane.jpg"]))
        img = cv2.imread("test/bus.jpg")
        _, jpg_data = cv2.imencode(".jpg", img)


if __name__ == '__main__':
    main()
