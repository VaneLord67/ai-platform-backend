from ais import app_yolo_cls
from model.cls_result import ClsResult


class YoloClsArg:
    def __init__(self, img_path):
        self.img_path = img_path


def call_cls_yolo(arg: YoloClsArg):
    args = []
    if arg.img_path:
        args.append(f"{arg.img_path}")
    cppClsResult = app_yolo_cls.main_func_wrapper(args)
    clsResult = ClsResult(cppClsResult.label, cppClsResult.class_name, cppClsResult.confidence)
    return clsResult


if __name__ == '__main__':
    arg = YoloClsArg(img_path=r"E:/GraduationDesign/tensorrt-alpha/data/6406402.jpg")
    clsResult = call_cls_yolo(arg)
    print(f"============={clsResult}=============")
