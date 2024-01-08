from nameko.events import event_handler, BROADCAST
from nameko.rpc import rpc

from microservice.ai_base import AIBaseService


class FaceService(AIBaseService):
    def single_image_cpp_call(self, img_path, output_path, hyperparameters):
        pass

    def video_cpp_call(self, video_path, output_video_path, output_jsonl_path, video_progress_key, hyperparameters,
                       task_id, unique_id):
        pass

    def camera_cpp_call(self, camera_id, hyperparameters, stop_signal_key, camera_data_queue_name, log_key):
        pass

    name = "face_service"

    # @event_handler("manage_service", name + "state_report", handler_type=BROADCAST, reliable_delivery=False)
    # def state_report(self, payload):
    #     return super().state_report(payload)

    @rpc
    def hello(self):
        return "face hello"

    @rpc
    def foo(self):
        return super().foo()

    @staticmethod
    def bar():
        print("hello face!")