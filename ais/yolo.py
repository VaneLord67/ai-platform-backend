import uuid
from typing import List

from ais import app_yolo
from model.box import Box
from model.hyperparameter import Hyperparameter


class YoloArg:
    def __init__(self, img_path=None, video_path=None, is_show=False,
                 save_path=r'E:/GraduationDesign/tensorOutput/',
                 size=640, batch_size=1, hyperparameters=None,
                 camera_id=None, queue_name=None, stop_signal_key=None, log_key=None, is_track=False,
                 video_output_path=None, video_progress_key=None, video_output_json_path=None):
        self.size = size
        self.batch_size = batch_size
        self.img_path = img_path
        self.video_path = video_path
        self.is_show = is_show
        self.save_path = save_path
        self.camera_id = camera_id
        self.queue_name = queue_name
        self.stop_signal_key = stop_signal_key
        self.log_key: str = log_key if log_key else str(uuid.uuid4())
        self.is_track: bool = is_track
        self.video_output_path = video_output_path
        self.video_progress_key = video_progress_key
        self.video_output_json_path = video_output_json_path

        if hyperparameters:
            self.wire_hyperparameters(hyperparameters)

        cnt = 0
        if self.img_path is not None:
            cnt += 1
        if self.video_path is not None:
            cnt += 1
        if self.camera_id is not None:
            cnt += 1
        if cnt != 1:
            raise ValueError("输入为空或不唯一", self.img_path, self.video_path, self.camera_id)
        if self.camera_id is not None and self.queue_name is None and self.stop_signal_key is None:
            raise ValueError("摄像头输入必须附带输出队列key和停止信号key")

    def wire_hyperparameters(self, hyperparameters: List[Hyperparameter]):
        for hp in hyperparameters:
            if hp.name == 'size':
                self.size = hp.value
            if hp.name == 'batch_size':
                self.batch_size = hp.value


def call_yolo(yoloArg: YoloArg):
    """
    这里用arg对象来构造命令行参数字符串
    """
    args = []
    args.append("app_yolo")  # 命令行参数的第一个位置为程序名，所以需要先添加一个字符串，写什么都行，不写的话cpp中命令行解析会出错
    args.append("--model=E:/GraduationDesign/yolov8n.trt")
    args.append(f"--size={yoloArg.size}")
    args.append(f"--batch_size={yoloArg.batch_size}")
    if yoloArg.img_path is not None:
        args.append(f"--img={yoloArg.img_path}")
    if yoloArg.video_path is not None:
        args.append(f"--video={yoloArg.video_path}")
    if yoloArg.camera_id is not None:
        args.append(f"--cam_id={yoloArg.camera_id}")
    if yoloArg.queue_name:
        args.append(f"--queueName={yoloArg.queue_name}")
    if yoloArg.stop_signal_key:
        args.append(f"--stopSignalKey={yoloArg.stop_signal_key}")
    if yoloArg.is_show:
        args.append("--show")
    if yoloArg.save_path:
        args.append(f"--savePath={yoloArg.save_path}")
    if yoloArg.log_key:
        args.append(f"--logKey={yoloArg.log_key}")
    if yoloArg.is_track:
        args.append(f"--track")
    if yoloArg.video_output_path:
        args.append(f"--videoOutputPath={yoloArg.video_output_path}")
    if yoloArg.video_output_json_path:
        args.append(f"--videoOutputJsonPath={yoloArg.video_output_json_path}")
    if yoloArg.video_progress_key:
        args.append(f"--videoProgressKey={yoloArg.video_progress_key}")
    print(f"args = {args}")
    cppFrames = app_yolo.main_func_wrapper(args)  # 调用cpp
    frames = []
    # 将cpp对象转为python对象
    for cppFrame in cppFrames:
        boxes = []
        for cppBox in cppFrame:
            box = Box(cppBox.left, cppBox.right, cppBox.bottom, cppBox.top, cppBox.confidence,
                      cppBox.label, cppBox.track_id)
            boxes.append(box)
        frames.append(boxes)
    return frames


if __name__ == '__main__':
    # --model=E:/GraduationDesign/yolov8n.trt
    # --size=640
    # --batch_size=1
    # --img=E:/GraduationDesign/tensorrt-alpha/data/6406402.jpg
    # --show
    # --savePath=E:/GraduationDesign/tensorOutput
    # yoloArg = YoloArg(img_path=r"E:/GraduationDesign/tensorrt-alpha/data/6406402.jpg")
    # frames = call_yolo(yoloArg)
    # print(frames)

    # track test
    # yoloArg = YoloArg(video_path=r"E:\GraduationDesign\TensorRT-YOLOv8-ByteTrack\videos\demo.mp4",
    #                   is_track=True, is_show=True)
    # frames = call_yolo(yoloArg)
    # frame_idx = 0
    # for frame in frames:
    #     # print(f'frame:{frame_idx}')
    #     # print(f'std::vector<byte_track::Object> frame{frame_idx};')
    #     for box in frame:
    #         pass
    #         # print(box)
    #         # print(f'add_element(frame{frame_idx}, {box.left}, {box.right}, {box.bottom}, {box.top}, {box.confidence}, {box.label});')
    #     frame_idx += 1

    # detect video test
    yoloArg = YoloArg(video_path=r"E:/GraduationDesign/tensorrt-alpha/data/people_h264.mp4",
                      is_show=True,
                      video_output_path=r"E:\GraduationDesign\ai-platform-backend\temp\video.mp4",
                      video_progress_key="video_progress",
                      video_output_json_path=r"E:\GraduationDesign\ai-platform-backend\temp\video.jsonl",
                      )
    frames = call_yolo(yoloArg)
    print(frames)

    # queue_name = "my_queue"
    # stopSignalKey = "stop"
    # client = create_redis_client()
    # client.delete(queue_name)
    # client.delete(stopSignalKey)
    # yoloArg = YoloArg(camera_id=0, batch_size=8, is_show=True,
    #                   save_path=None, queue_name=queue_name, stop_signal_key=stopSignalKey)
    # frames = call_yolo(yoloArg)

    # yolo_thread = threading.Thread(target=call_yolo, args=[yoloArg])
    # yolo_thread.start()

