import multiprocessing

import queue

import cv2


# 无缓存读取视频流
class UnbufferedVideoCapture:

    def __init__(self, video_capture_url):
        self.q = multiprocessing.Queue()
        self.param_queue = multiprocessing.Queue()
        self.log_queue = multiprocessing.Queue()
        self.process = multiprocessing.Process(target=self._reader, daemon=True,
                                               args=[self.q, self.param_queue, self.log_queue, video_capture_url])
        self.process.start()

    # 帧可用时立即读取帧，只保留最新的帧
    @staticmethod
    def _reader(q, param_queue, log_queue, cap_url):
        cap = cv2.VideoCapture(cap_url)
        if not cap.isOpened():
            log_queue.put("打开摄像头失败")
            return
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        param_queue.put((frame_width, frame_height))
        while True:
            ret, frame = cap.read()
            if not ret:
                q.put(None)
                break
            size = q.qsize()
            # print(f'qsize = {size}')
            if size > 2:
                for i in range(size - 2):
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        pass
            q.put(frame)

    def read(self):
        return self.q.get()

    def get_param(self):
        return self.param_queue.get()

    def get_log(self):
        if self.log_queue.empty():
            return None
        return self.log_queue.get()

    def release(self):
        if self.process:
            self.process.terminate()
