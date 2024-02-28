import sys

import cv2

sys.path.append("/home/hx/Yolov8-source/lib")

from ais import libutil_bytetrack as bytetrack_util
import libyolov8_trt as yolov8_trt
import faulthandler

faulthandler.enable()

'''
Yolov8Config:
.def_readwrite("nmsThresh", &Yolov8Config::nmsThresh)
.def_readwrite("objThresh", &Yolov8Config::objThresh)
.def_readwrite("classNum", &Yolov8Config::classNum)
.def_readwrite("boxesNum", &Yolov8Config::boxesNum)
.def_readwrite("src_width", &Yolov8Config::src_width)
.def_readwrite("src_height", &Yolov8Config::src_height)
.def_readwrite("trtModelPath", &Yolov8Config::trtModelPath)
.def_readwrite("inputNames", &Yolov8Config::inputNames)
.def_readwrite("outputNames", &Yolov8Config::outputNames)
.def_readwrite("maxBatchSize", &Yolov8Config::maxBatchSize)
.def_readwrite("batchSize", &Yolov8Config::batchSize)

DetectRect(下面的results):
.def_readwrite("xmin", &DetectRect::xmin)
.def_readwrite("ymin", &DetectRect::ymin)
.def_readwrite("w", &DetectRect::w)
.def_readwrite("h", &DetectRect::h)
.def_readwrite("label", &DetectRect::label)
.def_readwrite("score", &DetectRect::score)

Yolov8Detect类:
.def(py::init<Yolov8Config &>())                                     # 构造，初始化
.def("inference", &Yolov8Detect::inference, "inference for image")   # 推理api
.def("yolov8Reset", &Yolov8Detect::yolov8Reset, "reset the model")   # 重置模型

'''


def inference(img):
    yolov8_detector = init_yolo_detector(img)

    results, input_images = inference_by_yolo_detector(yolov8_detector, img)

    return results, input_images


def init_yolo_detector(img):
    # 配置文件参数定义
    config = init_yolo_detector_config(img.shape[1], img.shape[0])

    print(f'config src_size = {config.src_width}x{config.src_height}')
    # 初始化推理模型
    yolov8_detector = yolov8_trt.Yolov8Detect(config)

    return yolov8_detector


def init_yolo_detector_by_config(config):
    return yolov8_trt.Yolov8Detect(config)


def init_yolo_detector_config(src_width, src_height):
    # 配置文件参数定义
    config = yolov8_trt.Yolov8Config()
    config.nmsThresh = 0.5
    config.objThresh = 0.45

    config.trtModelPath = '/home/hx/Yolov8-source/data/model/yolov8s-d-t-b8.trt'
    config.maxBatchSize = 8

    config.batchSize = 1

    config.src_width = src_width
    config.src_height = src_height

    return config


def inference_by_yolo_detector(yolo_detector, img):
    # 调用推理api进行推理
    input_images = []
    for i in range(9):
        input_images.append(img)
    results = yolo_detector.inference(input_images)

    return results, input_images


def parse_results(results):
    parsed = []
    # 获取输出结果
    for i, frame_result in enumerate(results):
        # print("[DETECT INFO] Frame{} results: {} objections".format(i, len(frame_result)))
        # image_result是一张图像的推理结果，是包含DetectRect对象的列表
        for rect in frame_result:
            # print(f"xmin: {rect.xmin}, ymin: {rect.ymin}, w: {rect.w}, h: {rect.h}, label: {rect.label}, score: {rect.score}")
            xmin, ymin, w, h = rect.xmin, rect.ymin, rect.w, rect.h
            label, score = rect.label, rect.score
            parsed.append((xmin, ymin, w, h, label, score))
    return parsed


def parsed_to_json(parsed):
    json_list = []
    for rect in parsed:
        xmin, ymin, w, h, label, score = rect
        json_item = {
            'xmin': xmin,
            'ymin': ymin,
            'w': w,
            'h': h,
            'label': label,
            'score': score,
        }
        json_list.append(json_item)
    return [json_list]


def draw_results(input_images, results, save_path=None):
    # 获取输出结果
    for i, frame_result in enumerate(results):
        # print("[DETECT INFO] Frame{} results: {} objections".format(i, len(frame_result)))
        # image_result是一张图像的推理结果，是包含DetectRect对象的列表
        for rect in frame_result:
            # print(f"xmin: {rect.xmin}, ymin: {rect.ymin}, w: {rect.w}, h: {rect.h}, label: {rect.label}, score: {rect.score}")
            xmin, ymin, w, h = rect.xmin, rect.ymin, rect.w, rect.h

            # 在图像上绘制矩形框
            cv2.rectangle(input_images[i], (int(xmin), int(ymin)), (int(xmin + w), int(ymin + h)), (0, 255, 0), 2)

            # 在矩形框上方绘制标签和置信度
            label_text = f"cls{int(rect.label)} conf{rect.score:.2f}"
            cv2.putText(input_images[i], label_text, (int(xmin), int(ymin) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (0, 255, 0), 2)
        if save_path:
            # 'results/frame_' + str(i) + '_results.jpg'
            cv2.imwrite(save_path, input_images[i])


def draw_track_results(input_images, yolo_rects, save_path=None):
    for yolo_rect in yolo_rects:
        xmin, ymin, w, h = yolo_rect.xmin, yolo_rect.ymin, yolo_rect.w, yolo_rect.h
        # 在图像上绘制矩形框
        cv2.rectangle(input_images[0], (int(xmin), int(ymin)), (int(xmin + w), int(ymin + h)), (0, 255, 0), 2)
        # 在矩形框上方绘制标签和置信度和track_id
        label_text = f"cls{int(yolo_rect.label)} conf{yolo_rect.score:.2f} track_id{int(yolo_rect.track_id)}"
        cv2.putText(input_images[0], label_text, (int(xmin), int(ymin) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 255, 0), 2)
    if save_path:
        # 'results/frame_' + str(i) + '_results.jpg'
        cv2.imwrite(save_path, input_images[0])


def convert_parsed_to_yolo_rect(parsed):
    yolo_rects = []
    for parse_item in parsed:
        xmin, ymin, w, h, label, score = parse_item
        yolo_rect = bytetrack_util.ByteTrackUtilYoloRect()
        yolo_rect.xmin = xmin
        yolo_rect.ymin = ymin
        yolo_rect.w = w
        yolo_rect.h = h
        yolo_rect.label = int(label)
        yolo_rect.score = score
        yolo_rects.append(yolo_rect)
    return yolo_rects


def pic_infer_test():
    image = cv2.imread('/home/hx/Yolov8-source/data/image/bus.jpg')
    results, input_images = inference(image)
    frames = parse_results(results)
    print(frames)
    draw_results(input_images, results, save_path='test.jpg')


def video_infer_test():
    video_capture = cv2.VideoCapture("people_h264.mp4")
    # 检查视频文件是否成功打开
    if not video_capture.isOpened():
        print("Error: Unable to open video file.")
        exit()
    frame_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frame_count = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(video_capture.get(cv2.CAP_PROP_FPS))
    current_frame_count = 0

    # 逐帧读取视频
    while True:
        # 读取一帧
        ret, image = video_capture.read()
        # 检查是否成功读取帧
        if not ret:
            break
        current_frame_count += 1
        progress_str = "%.2f" % (current_frame_count / total_frame_count)
        print(f'progress_str = {progress_str}')
        # 对帧进行处理
        results, input_images = inference(image)

        rects = parse_results(results)
        json_items = []
        for rect in rects:
            xmin, ymin, w, h, label, score = rect
            json_item = {
                'xmin': xmin,
                'ymin': ymin,
                'w': w,
                'h': h,
                'label': label,
                'score': score,
            }
            json_items.append(json_item)
        # 释放资源
        video_capture.release()


if __name__ == '__main__':
    video_infer_test()
