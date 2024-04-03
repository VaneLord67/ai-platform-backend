import numpy as np

from ais import tensorrt_cls_pybind
from common.util import clear_video_temp_resource
from microservice.recognition import RecognitionService
from scripts.video_common import parse_video_command_args
from video.video_template import VideoTemplate


def video_cpp_call(video_path, video_output_path, video_output_json_path, video_progress_key,
                   hyperparameters, task_id, service_unique_id):
    try:
        config = tensorrt_cls_pybind.ClassifierConfig()
        config.model_file_path = "E:/GraduationDesign/yolov8n-cls.trt"
        model = tensorrt_cls_pybind.Classifier(config)

        def ai_func(image):
            idx, score = model.inference(np.asarray(image, dtype=np.uint8))
            cls_json = {
                'label': idx,
                'score': score,
            }
            return cls_json

        video_template = VideoTemplate(video_path, video_output_path, video_output_json_path, video_progress_key,
                                       hyperparameters, task_id, service_unique_id, RecognitionService.name, ai_func)
        video_template.loop_process()
    finally:
        clear_video_temp_resource(video_path, video_output_path, video_output_json_path)


if __name__ == '__main__':
    video_command_args = parse_video_command_args()
    video_cpp_call(*video_command_args)
