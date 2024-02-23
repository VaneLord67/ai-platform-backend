import sys

import cv2

sys.path.append("/home/hx/Yolov8-source/lib")

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


def inference(image):
    # 配置文件参数定义
    config = yolov8_trt.Yolov8Config()
    config.nmsThresh = 0.5
    config.objThresh = 0.45

    config.trtModelPath = '/home/hx/Yolov8-source/data/model/yolov8s-d-t-b8.trt'
    config.maxBatchSize = 8

    config.batchSize = 1

    config.src_width = image.shape[1]
    config.src_height = image.shape[0]

    # 初始化推理模型
    yolov8_detector = yolov8_trt.Yolov8Detect(config)

    # 调用推理api进行推理
    input_images = []
    for i in range(9):
        input_images.append(image)
    results = yolov8_detector.inference(input_images)

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
    for frame in parsed:
        frame_list = []
        for rect in frame:
            json_item = {
                'xmin': rect.xmin,
                'ymin': rect.ymin,
                'w': rect.w,
                'h': rect.h,
                'label': rect.label,
                'score': rect.score,
            }
            frame_list.append(json_item)
        json_list.append(frame_list)
    return json_list


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


if __name__ == '__main__':
    image = cv2.imread('/home/hx/Yolov8-source/data/image/bus.jpg')
    results, input_images = inference(image)
    frames = parse_results(results)
    print(frames)
    draw_results(input_images, results, save_path='test.jpg')
