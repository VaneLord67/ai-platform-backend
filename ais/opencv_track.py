from typing import Union, List

from ais import track_opencv
from model.hyperparameter import Hyperparameter
from model.track_result import TrackResult


class TrackArg:
    def __init__(self, video_path=None, save_path=None, roi_rec=None, hyperparameters=None, is_show=False):
        self.video_path: Union[str, None] = video_path
        self.is_show = is_show
        self.save_path: Union[str, None] = save_path
        self.roi_rec: Union[TrackResult, None] = roi_rec
        self.hyperparameters: Union[List[Hyperparameter], None] = hyperparameters
        self.wire_roi_rec(hyperparameters)

    def wire_roi_rec(self, hyperparameters: List[Hyperparameter]):
        if hyperparameters is None:
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
    print(f"args = {args}")
    cppResults = track_opencv.main_func_wrapper(args)
    trackResults = []
    for cppResult in cppResults:
        trackResult = TrackResult(cppResult.x, cppResult.y, cppResult.width, cppResult.height)
        trackResults.append(trackResult)
    return trackResults


if __name__ == '__main__':
    roi = TrackResult(844, 337, 441, 610)
    arg = TrackArg(video_path=r"E:/GraduationDesign/track_test_tiny.mp4", is_show=True, roi_rec=roi,
                   save_path="E:/GraduationDesign/tensorOutput/")
    results = call_track(arg)
    print(f"results = {results}")
