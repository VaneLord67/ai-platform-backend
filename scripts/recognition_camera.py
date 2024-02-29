from ais.yolo_cls import YoloClsArg, call_cls_yolo
from common.util import clear_camera_temp_resource
from microservice.recognition import RecognitionService
from scripts.camera_common import after_camera_call, parse_camera_command_args


def camera_cpp_call(camera_id, hyperparameters, stop_signal_key,
                    camera_data_queue_name, log_key, task_id, service_unique_id,
                    camera_output_path, camera_output_json_path):
    try:
        arg = YoloClsArg(camera_id=camera_id,
                         stop_signal_key=stop_signal_key, queue_name=camera_data_queue_name,
                         video_output_path=camera_output_path, video_output_json_path=camera_output_json_path,
                         hyperparameters=hyperparameters, log_key=log_key)
        call_cls_yolo(arg)
        after_camera_call(camera_output_path, camera_output_json_path,
                          task_id, RecognitionService.name, service_unique_id)
    finally:
        clear_camera_temp_resource(camera_output_path, camera_output_json_path)


if __name__ == '__main__':
    camera_id, hps, stop_signal_key, \
        camera_data_queue_name, log_key, task_id, service_unique_id, \
        camera_output_path, camera_output_json_path = parse_camera_command_args()
    camera_cpp_call(camera_id, hps, stop_signal_key,
                    camera_data_queue_name, log_key, task_id, service_unique_id,
                    camera_output_path, camera_output_json_path)
