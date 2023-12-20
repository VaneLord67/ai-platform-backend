from ais import app_yolo_cls
from model.cls_result import ClsResult


class YoloClsArg:
    def __init__(self, img_path=None, hyperparameters=None, queue_name=None, stop_signal_key=None,
                 video_path=None, camera_id=None):
        self.img_path = img_path
        self.video_path = video_path
        self.camera_id = camera_id
        self.hyperparameters = hyperparameters
        self.queue_name = queue_name
        self.stop_signal_key = stop_signal_key

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
