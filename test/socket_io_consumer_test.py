import cv2
import numpy as np
import socketio

if __name__ == '__main__':
    # 创建 Socket.IO 客户端
    sio = socketio.Client()

    # 定义连接 Namespace 的处理函数
    @sio.on('connect', namespace='/test')
    def on_connect():
        print('Connected to /test Namespace!')
        sio.emit('post_consumer_id', namespace='/test')

    @sio.on('start_camera_retrieve', namespace='/test')
    def on_start_camera_retrieve():
        print('start data retrieve!')
        sio.emit('camera_retrieve', namespace='/test')

    @sio.on('camera_data', namespace='/test')
    def on_camera_data(data):
        print('Message type:', type(data))
        # print('Message received:', data)
        image_array = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        # 显示图像
        cv2.imshow('Image', img)
        cv2.waitKey(0)


    # 启动客户端
    sio.connect('http://localhost:8086/test')  # 修改为服务器地址和 Namespace 名称

    # 运行客户端，保持连接
    sio.wait()
