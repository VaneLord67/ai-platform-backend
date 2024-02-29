import uuid

import platform
if platform.system() == 'Linux':
    from ais import libapp_yolo_cls as app_yolo_cls
elif platform.system() == 'Windows':
    from ais import app_yolo_cls as app_yolo_cls
else:
    raise Exception("Unsupported platform")
from model.cls_result import ClsResult


class YoloClsArg:
    def __init__(self, img_path=None, hyperparameters=None, queue_name=None, stop_signal_key=None,
                 video_path=None, camera_id=None, log_key=None,
                 video_output_path=None, video_progress_key=None, video_output_json_path=None):
        self.img_path = img_path
        self.video_path = video_path
        self.camera_id = camera_id
        self.hyperparameters = hyperparameters
        self.queue_name = queue_name
        self.stop_signal_key = stop_signal_key
        self.log_key: str = log_key if log_key else str(uuid.uuid4())
        self.video_output_path = video_output_path
        self.video_progress_key = video_progress_key
        self.video_output_json_path = video_output_json_path

        cnt = 0
        if self.img_path is not None:
            cnt += 1
        if self.video_path is not None:
            cnt += 1
        if self.camera_id is not None:
            cnt += 1
        if cnt != 1:
            raise ValueError("输入为空或不唯一", self.img_path, self.video_path, self.camera_id)


def call_cls_yolo(arg: YoloClsArg):
    args = []
    args.append("app_yolo_cls")
    if arg.img_path:
        args.append(f"--img={arg.img_path}")
    if arg.video_path:
        args.append(f"--video={arg.video_path}")
    if arg.camera_id is not None:
        args.append(f"--cam_id={arg.camera_id}")
    if arg.stop_signal_key:
        args.append(f"--stopSignalKey={arg.stop_signal_key}")
    if arg.queue_name:
        args.append(f"--queueName={arg.queue_name}")
    if arg.log_key:
        args.append(f"--logKey={arg.log_key}")
    if arg.video_output_path:
        args.append(f"--videoOutputPath={arg.video_output_path}")
    if arg.video_output_json_path:
        args.append(f"--videoOutputJsonPath={arg.video_output_json_path}")
    if arg.video_progress_key:
        args.append(f"--videoProgressKey={arg.video_progress_key}")
    print(f"args = {args}")
    cppClsResults = app_yolo_cls.main_func_wrapper(args)
    clsResults = []
    for cppClsResult in cppClsResults:
        clsResult = ClsResult(cppClsResult.label, cppClsResult.class_name, cppClsResult.confidence)
        clsResults.append(clsResult)
    return clsResults


if __name__ == '__main__':
    # arg = YoloClsArg(video_path=r"E:/GraduationDesign/tensorrt-alpha/data/people_h264.mp4")
    # clsResults = call_cls_yolo(arg)
    # print(f"============={clsResults}=============")
    # print(f"results len = {len(clsResults)}")

    # arg = YoloClsArg(img_path=r"E:/GraduationDesign/tensorrt-alpha/data/6406402.jpg")
    # clsResult = call_cls_yolo(arg)
    # print(f"============={clsResult}=============")

    arg = YoloClsArg(camera_id=0, queue_name='my_queue', stop_signal_key="stop")
    call_cls_yolo(arg)
