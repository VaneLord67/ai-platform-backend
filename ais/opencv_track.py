import uuid
from datetime import timedelta
from typing import Union, List

import redis

from ais import track_opencv
from common.config import config
from common.util import create_redis_client
from model.hyperparameter import Hyperparameter
from model.track_result import TrackResult


class TrackArg:
    def __init__(self, video_path=None, save_path=None, roi_rec=None,
                 hyperparameters=None, is_show=False,
                 cam_id=None, stop_signal_key=None, queue_name=None, roi_key=None, log_key=None):
        self.video_path: Union[str, None] = video_path
        self.is_show = is_show
        self.save_path: Union[str, None] = save_path
        self.roi_rec: Union[TrackResult, None] = roi_rec
        self.hyperparameters: Union[List[Hyperparameter], None] = hyperparameters

        self.cam_id = cam_id
        self.stop_signal_key = stop_signal_key
        self.queue_name = queue_name
        self.roi_key = roi_key
        self.log_key: str = log_key if log_key else str(uuid.uuid4())

        cnt = 0
        if self.video_path:
            cnt += 1
        if self.cam_id is not None:
            cnt += 1
        if cnt != 1:
            raise ValueError("输入为空或不唯一")

        # if self.cam_id is not None:
        #     if self.queue_name is None or self.stop_signal_key is None or self.roi_key is None:
        #         raise ValueError("摄像头输入缺少参数")

        self.wire_roi_rec(hyperparameters)

    def wire_roi_rec(self, hyperparameters: List[Hyperparameter]):
        if hyperparameters is None:
            return
        if self.cam_id is not None:
            return
        roi_x = None
        roi_y = None
        roi_width = None
        roi_height = None
        for hp in hyperparameters:
            if hp.name == 'roi_x':
                roi_x = hp.value
            elif hp.name == 'roi_y':
                roi_y = hp.value
            elif hp.name == 'roi_width':
                roi_width = hp.value
            elif hp.name == 'roi_height':
                roi_height = hp.value
        if roi_x and roi_y and roi_width and roi_height:
            self.roi_rec = TrackResult(roi_x, roi_y, roi_width, roi_height)


def call_track(arg: TrackArg):
    args = ["track_opencv"]
    if arg.is_show:
        args.append(f"--show")
    if arg.video_path:
        args.append(f"--video={arg.video_path}")
    if arg.save_path:
        args.append(f"--savePath={arg.save_path}")
    if arg.roi_rec:
        args.append(f"--roi_x={arg.roi_rec.x}")
        args.append(f"--roi_y={arg.roi_rec.y}")
        args.append(f"--roi_width={arg.roi_rec.width}")
        args.append(f"--roi_height={arg.roi_rec.height}")
    if arg.cam_id is not None:
        args.append(f"--cam_id={arg.cam_id}")
    if arg.stop_signal_key:
        args.append(f"--stopSignalKey={arg.stop_signal_key}")
    if arg.queue_name:
        args.append(f"--queueName={arg.queue_name}")
    if arg.roi_key:
        args.append(f"--roiKey={arg.roi_key}")
    if arg.log_key:
        args.append(f"--logKey={arg.log_key}")
    print(f"args = {args}")
    cppResults = track_opencv.main_func_wrapper(args)
    trackResults = []
    for cppResult in cppResults:
        trackResult = TrackResult(cppResult.x, cppResult.y, cppResult.width, cppResult.height)
        trackResults.append(trackResult)
    return trackResults


def set_roi_to_redis(roi: TrackResult, roi_key: str, client: redis.StrictRedis):
    roi_x_key = roi_key + "_x"
    roi_y_key = roi_key + "_y"
    roi_width_key = roi_key + "_width"
    roi_height_key = roi_key + "_height"

    client.setex(name=roi_x_key, value=roi.x, time=timedelta(minutes=5))
    client.setex(name=roi_y_key, value=roi.y, time=timedelta(minutes=5))
    client.setex(name=roi_width_key, value=roi.width, time=timedelta(minutes=5))
    client.setex(name=roi_height_key, value=roi.height, time=timedelta(minutes=5))

    client.setex(name=roi_key, value="", time=timedelta(minutes=1))


if __name__ == '__main__':
    # roi = TrackResult(844, 337, 441, 610)
    # roi = TrackResult(287, 23, 86, 320)
    # arg = TrackArg(video_path=r"E:/GraduationDesign/track_test_tiny.mp4", is_show=True, roi_rec=roi,
    #                save_path="E:/GraduationDesign/tensorOutput/")
    # results = call_track(arg)
    # print(f"results = {results}")

    client = create_redis_client()
    stop_signal_key = "stop"
    queue_name = "my_queue"
    roi_key = "roi"
    # set_roi_to_redis(roi, roi_key, client)
    arg = TrackArg(cam_id=0, stop_signal_key=stop_signal_key, queue_name=queue_name, is_show=True)
    results = call_track(arg)
    print(f"results = {results}")
