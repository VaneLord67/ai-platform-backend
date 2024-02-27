import multiprocessing

import cv2
import queue
import threading


# 无缓存读取视频流
class UnbufferedVideoCapture:

    def __init__(self, video_capture):
        self.cap = video_capture
        self.q = multiprocessing.Queue()
        self.process = multiprocessing.Process(target=self._reader, daemon=True,
                                               args=[self.q, self.cap])

    # 帧可用时立即读取帧，只保留最新的帧
    @staticmethod
    def _reader(q, cap):
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            size = q.qsize()
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
