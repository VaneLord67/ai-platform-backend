import logging
import multiprocessing
import queue

from video.sei_parser import MessageType, SEIParser


class UnbufferedSEIParser:

    def __init__(self, rtmp_url):
        self.q = multiprocessing.Queue()
        self.param_queue = multiprocessing.Queue()
        self.sei_queue = multiprocessing.Queue()
        self.stop_queue = multiprocessing.Queue()
        self.process = multiprocessing.Process(target=self._reader, daemon=True,
                                               args=[self.q, self.param_queue, self.sei_queue,
                                                     rtmp_url, self.stop_queue])
        self.process.start()

    # 帧可用时立即读取帧，只保留最新的帧
    @staticmethod
    def _reader(q, param_queue, sei_queue, rtmp_url, stop_queue):
        sei_parser = SEIParser(rtmp_url)
        ffmpeg_parser_gen = sei_parser.start()
        ffmpeg_parse_data = next(ffmpeg_parser_gen)
        if ffmpeg_parse_data[0] == MessageType.PARAMETER_TYPE.value:
            width = ffmpeg_parse_data[1]
            height = ffmpeg_parse_data[2]
            param_queue.put((width, height))
        for ffmpeg_parse_data in ffmpeg_parser_gen:
            if stop_queue.qsize() > 0:
                sei_parser.release()
                q.put(None)
                break
            if ffmpeg_parse_data[0] == MessageType.SEI.value:
                sei_str = ffmpeg_parse_data[1]
                sei_queue.put(sei_str)
                continue
            if ffmpeg_parse_data[0] != MessageType.IMAGE_FRAME.value:
                logging.error("MessageType mismatch")
                q.put(None)
                break
            image = ffmpeg_parse_data[1]
            q.put(image)
            size = q.qsize()
            if size > 2:
                for i in range(size - 2):
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        pass
        q.put(None)

    def read(self):
        return self.q.get()

    def get_param(self):
        return self.param_queue.get()

    def get_sei(self):
        try:
            ret = self.sei_queue.get_nowait()
        except queue.Empty:
            ret = None
        return ret

    def release(self):
        print("unbuffered_sei_parser release")
        self.stop_queue.put(None)
        if self.process:
            self.process.join(timeout=5)
            self.process.terminate()
