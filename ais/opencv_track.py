from typing import Union, List

from ais import track_opencv
from model.hyperparameter import Hyperparameter
from model.track_result import TrackResult


class TrackArg:
    def __init__(self, video_path=None, save_path=None, roi_rec=None, hyperparameters=None):
        self.video_path: Union[str, None] = video_path
        self.save_path: Union[str, None] = save_path
        self.roi_rec: Union[TrackResult, None] = roi_rec
        self.hyperparameters: Union[List[Hyperparameter], None] = hyperparameters


def call_track(arg: TrackArg):
    args = []
    if arg.video_path:
        args.append(f"--video={arg.video_path}")
    if arg.save_path:
        args.append(f"--savePath={arg.save_path}")
    if arg.roi_rec:
        args.append(f"--roi_x={arg.roi_rec.x} --roi_y={arg.roi_rec.y} "
                    f"--roi_width={arg.roi_rec.width} --roi_height={arg.roi_rec.height}")
    cppResults = track_opencv.main_func_wrapper(args)
    trackResults = []
    for cppResult in cppResults:
        trackResult = TrackResult(cppResult.x, cppResult.y, cppResult.width, cppResult.height)
        trackResults.append(trackResult)
    return trackResults


if __name__ == '__main__':
    arg = TrackArg(video_path=r"E:/GraduationDesign/track_test.mp4")
    results = call_track(arg)
    print(f"results = {results}")
