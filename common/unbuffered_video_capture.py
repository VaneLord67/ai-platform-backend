import multiprocessing

import queue

import cv2


# 无缓存读取视频流
class UnbufferedVideoCapture:

    def __init__(self, video_capture_url):
        self.q = multiprocessing.Queue()
        self.process = multiprocessing.Process(target=self._reader, daemon=True,
                                               args=[self.q, video_capture_url])
        self.process.start()

    # 帧可用时立即读取帧，只保留最新的帧
    @staticmethod
    def _reader(q, cap_url):
        cap = cv2.VideoCapture(cap_url)
        while True:
            ret, frame = cap.read()
            if not ret:
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

    def release(self):
        if self.process:
            self.process.terminate()