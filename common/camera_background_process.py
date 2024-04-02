import logging
import multiprocessing

import cv2


class CameraBackgroundProcess:
    """
    摄像头后台进程，负责写入jsonl文件和mp4文件
    """
    def __init__(self, camera_output_path, camera_output_json_path, frame_width, frame_height):
        self.camera_data_queue = multiprocessing.Queue()
        self.camera_json_queue = multiprocessing.Queue()
        self.process = multiprocessing.Process(target=self._background, daemon=True,
                                               args=[camera_output_path, camera_output_json_path,
                                                     self.camera_data_queue, self.camera_json_queue,
                                                     frame_width, frame_height])
        self.process.start()

    @staticmethod
    def _background(camera_output_path, camera_output_json_path, camera_data_queue, camera_json_queue,
                    frame_width, frame_height):
        json_file = open(camera_output_json_path, 'w')
        out = cv2.VideoWriter(camera_output_path, cv2.VideoWriter_fourcc(*'avc1'), 30, (frame_width, frame_height))
        while True:
            image = camera_data_queue.get()
            if image is None:
                break
            out.write(image)
            json_data = camera_json_queue.get()
            json_file.write(json_data + '\n')
        out.release()
        json_file.close()

    def put(self, image, json_data):
        self.camera_data_queue.put(image)
        self.camera_json_queue.put(json_data)

    def release(self):
        logging.info("release camera background process")
        self.camera_data_queue.put(None)  # None表示结束信号，子进程接收到None后释放资源，保存文件
        self.process.join()
