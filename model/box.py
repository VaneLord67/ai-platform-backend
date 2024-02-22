
from common.util import JsonBase

class_names = ["person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
               "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
               "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
               "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
               "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
               "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
               "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard",
               "cell phone",
               "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors",
               "teddy bear",
               "hair drier", "toothbrush"]


class Box(JsonBase):
    def __init__(self, left=None, right=None, bottom=None, top=None, confidence=None, label=None, track_id=None):
        super().__init__()
        self.left: float = left
        self.right: float = right
        self.bottom: float = bottom
        self.top: float = top
        self.confidence: float = confidence
        self.label: int = label
        self.class_name: str = class_names[label] if label is not None else ""
        self.track_id: int = track_id

    def __json__(self):
        return self.to_json()
