import threading
import time

from nameko.events import event_handler, BROADCAST, SERVICE_POOL
from nameko.rpc import rpc
from nameko.web.handlers import http
from werkzeug import Request

from common.api_response import APIResponse
from common.error_code import ErrorCodeEnum
from common.util import connect_to_database
from microservice.redis_storage import RedisStorage
from model.ai_model import AIModel
from model.detection_output import DetectionOutput
from model.hyperparameter import Hyperparameter
from model.service_info import ServiceInfo, ServiceReadyState, ServiceRunningState
from model.support_input import *


def initStateInfo():
    serviceInfo = ServiceInfo()

    hyperparameter = Hyperparameter()
    hyperparameter.type = "integer"
    hyperparameter.name = "置信度阈值"

    model = AIModel()
    model.field = "检测"
    model.hyperparameters = [hyperparameter]
    model.name = "yoloV8"
    model.support_input = [SINGLE_PICTURE_URL_TYPE]

    serviceInfo.model = model
    return serviceInfo


class DetectionService:
    name = "detection_service"
    serviceInfo = initStateInfo()
    state_lock = threading.Lock()
    redis_storage = RedisStorage()

    def __init__(self):
        self.conn = connect_to_database()

    @event_handler("manage_service", name + "state_report", handler_type=BROADCAST, reliable_delivery=False)
    def state_report(self, payload):
        redis_list_key = payload
        self.state_lock.acquire()
        try:
            state_string = self.serviceInfo.__str__()
            self.redis_storage.client.rpush(redis_list_key, state_string)
        finally:
            self.state_lock.release()

    @event_handler("manage_service", name + "close_event", handler_type=BROADCAST, reliable_delivery=False)
    def close_event_handler(self, payload):
        print("receive close event")
        raise KeyboardInterrupt

    @event_handler("manage_service", name + "close_one_event", handler_type=SERVICE_POOL, reliable_delivery=False)
    def close_one_event_handler(self, payload):
        print("receive close one event")
        raise KeyboardInterrupt

    # @http('POST', '/model/detect')
    # def detectHTTPHandler(self, request: Request):
    #     json_data = request.get_json()
    #     hyperparameter = Hyperparameter().from_dict(json_data['hyperparameter']) \
    #         if 'hyperparameter' in json_data else Hyperparameter()
    #     supportInput = SupportInput().from_dict(json_data['support_input'])
    #     if supportInput.type == SINGLE_PICTURE_URL_TYPE:
    #         output = DetectionOutput()
    #         output.url = "https://img2.baidu.com/it/u=2933220116,3086945787&fm=253&fmt=auto&app=138&f=JPEG?w=744&h=500"
    #         return APIResponse.success_with_data(output).__str__()
    #     return APIResponse.fail_with_error_code_enum(ErrorCodeEnum.UNSUPPORTED_INPUT_ERROR)

    @rpc
    def detectRPCHandler(self, args: dict):
        self.state_lock.acquire()
        try:
            self.serviceInfo.state = ServiceRunningState
            hyperparameter = Hyperparameter().from_dict(args['hyperparameter']) \
                if 'hyperparameter' in args else Hyperparameter()
            supportInput = SupportInput().from_dict(args['supportInput'])
            output = DetectionOutput()
            if supportInput.type == SINGLE_PICTURE_URL_TYPE:
                # handle input
                time.sleep(1)
                output.url = "https://img2.baidu.com/it/u=2933220116,3086945787&fm=253&fmt=auto&app=138&f=JPEG?w=744&h=500"
                return output
            return output
        finally:
            self.serviceInfo.state = ServiceReadyState
            self.state_lock.release()
