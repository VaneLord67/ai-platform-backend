from ais.yolo_cls import YoloClsArg, call_cls_yolo
from common.util import clear_video_temp_resource
from scripts.video_common import after_video_call, parse_video_command_args


def video_cpp_call(video_path, video_output_path, video_output_json_path, video_progress_key,
                   hyperparameters, task_id, service_unique_id):
    try:
        arg = YoloClsArg(video_path=video_path, hyperparameters=hyperparameters,
                         video_output_path=video_output_path,
                         video_output_json_path=video_output_json_path,
                         video_progress_key=video_progress_key,
                         )
        call_cls_yolo(arg)
        after_video_call(video_output_path, video_output_json_path,
                         task_id, "recognition_service", service_unique_id)
    finally:
        clear_video_temp_resource(video_path, video_output_path, video_output_json_path)


if __name__ == '__main__':
    video_path, video_output_path, video_output_json_path, video_progress_key, \
        hps, task_id, service_unique_id = parse_video_command_args()
    video_cpp_call(video_path, video_output_path, video_output_json_path, video_progress_key,
                   hps, task_id, service_unique_id)
