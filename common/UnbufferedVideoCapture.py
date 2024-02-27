import cv2
import queue
import threading


# 无缓存读取视频流
class UnbufferedVideoCapture:

    def __init__(self, video_capture):
        self.cap = video_capture
        self.q = queue.Queue()
        t = threading.Thread(target=self._reader)
        t.daemon = True
        t.start()

    # 帧可用时立即读取帧，只保留最新的帧
    def _reader(self):
        print('_reader thread start')
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            if not self.q.empty():
                size = self.q.qsize()
                if size > 2:
                    for i in range(size - 2):
                        try:
                            self.q.get_nowait()
                        except queue.Empty:
                            pass
                try:
                    self.q.get_nowait()  # nowait非阻塞。若队列空则抛出异常
                except queue.Empty:
                    pass
            self.q.put(frame)

    def read(self):
        return self.q.get()
