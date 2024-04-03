from ais import tensorrt_cls_pybind
from common.util import clear_camera_temp_resource
from microservice.recognition import RecognitionService
from scripts.camera_common import after_camera_call, parse_camera_command_args
from video.camera_template import CameraTemplate


def camera_cpp_call(camera_id, hyperparameters, namespace, task_id, service_unique_id,
                    camera_output_path, camera_output_json_path):
    try:
        config = tensorrt_cls_pybind.ClassifierConfig()
        config.model_file_path = "E:/GraduationDesign/yolov8n-cls.trt"
        model = tensorrt_cls_pybind.Classifier(config)

        def ai_func(img):
            idx, score = model.inference(img)
            cls_json = [{
                'label': idx,
                'score': score,
            }]
            return cls_json

        camera_template = CameraTemplate(camera_id, hyperparameters, namespace, task_id, service_unique_id,
                                         camera_output_path, camera_output_json_path, RecognitionService.name, ai_func)
        camera_template.loop_process()
    finally:
        clear_camera_temp_resource(camera_output_path, camera_output_json_path)


if __name__ == '__main__':
    camera_args = parse_camera_command_args()
    camera_cpp_call(*camera_args)
