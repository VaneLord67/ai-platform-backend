from nameko.events import event_handler, BROADCAST

from microservice.ai_base import AIBaseService
from microservice.manage import ManageService
from model.ai_model import AIModel
from model.service_info import ServiceInfo
from model.support_input import *


def init_state_info():
    service_info = ServiceInfo()

    model = AIModel()
    model.field = "跟踪"
    model.hyperparameters = []
    model.name = "yoloV8 + ByteTrack"
    model.support_input = [VIDEO_URL_TYPE, CAMERA_TYPE]

    service_info.model = model
    return service_info


class TrackService(AIBaseService):
    name = "track_service"

    service_info = init_state_info()

    video_script_name = "scripts/track_hx_video.py"
    camera_script_name = "scripts/track_hx_camera.py"

    @event_handler(ManageService.name, name + "state_report", handler_type=BROADCAST, reliable_delivery=False)
    def state_report(self, payload):
        super().state_report(payload)

    @event_handler(ManageService.name, name + "close_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_event_handler(self, payload):
        super().close_event_handler(payload)

    @event_handler(ManageService.name, name + "close_one_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_one_event_handler(self, payload):
        super().close_event_handler(payload)

    @event_handler(ManageService.name, name + "state_change", handler_type=BROADCAST, reliable_delivery=False)
    def state_to_ready_handler(self, payload):
        super().state_to_ready_handler(payload)

