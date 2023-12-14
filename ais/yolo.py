from ais import app_yolo

from model.box import Box


class YoloArg:
    def __init__(self, img_path=None, video_path=None, is_show=False,
                 save_path=r'E:/GraduationDesign/tensorOutput/',
                 size=640, batch_size=1):
        self.size = size
        self.batch_size = batch_size
        self.img_path = img_path
        self.video_path = video_path
        self.is_show = is_show
        self.save_path = save_path

        if not self.img_path and not self.video_path:
            raise ValueError("img_path or video_path should not be None")


def call_yolo(yoloArg: YoloArg):
    args = []
    args.append("app_yolo")
    args.append("--model=E:/GraduationDesign/yolov8n.trt")
    args.append(f"--size={yoloArg.size}")
    args.append(f"--batch_size={yoloArg.batch_size}")
    if yoloArg.img_path:
        args.append(f"--img={yoloArg.img_path}")
    if yoloArg.video_path:
        args.append(f"--video={yoloArg.video_path}")
    if yoloArg.is_show:
        args.append("--show")
    if yoloArg.save_path:
        args.append(f"--savePath={yoloArg.save_path}")
    cppFrames = app_yolo.main_func_wrapper(args)
    frames = []
    for cppFrame in cppFrames:
        boxes = []
        for cppBox in cppFrame:
            box = Box(cppBox.left, cppBox.right, cppBox.bottom, cppBox.top, cppBox.confidence, cppBox.label)
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
    yoloArg = YoloArg(img_path=r"E:/GraduationDesign/tensorrt-alpha/data/6406402.jpg")
    frames = call_yolo(yoloArg)
    print(frames)
