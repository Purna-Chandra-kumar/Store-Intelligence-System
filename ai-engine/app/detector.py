"""YOLO detector wrapper.

Wrapping Ultralytics gives us:
  * one place to swap models (yolov8n → yolo11n → custom)
  * a stable output contract that doesn't leak ultralytics types
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from ultralytics import YOLO

from .config import settings


@dataclass(frozen=True)
class Detection:
    xyxy: tuple[float, float, float, float]   # x1, y1, x2, y2
    conf: float
    cls: int


class PersonDetector:
    """Detects persons (COCO class 0). Stateless, thread-safe per instance."""

    def __init__(self) -> None:
        self._model = YOLO(settings.yolo_model)
        self._conf = settings.yolo_conf
        self._device = settings.device

    def __call__(self, frame: np.ndarray) -> list[Detection]:
        results = self._model.predict(
            frame,
            conf=self._conf,
            classes=[0],
            verbose=False,
            device=self._device,
        )
        out: list[Detection] = []
        if not results:
            return out
        boxes = results[0].boxes
        if boxes is None:
            return out
        xyxy = boxes.xyxy.cpu().numpy()
        conf = boxes.conf.cpu().numpy()
        cls = boxes.cls.cpu().numpy().astype(int)
        for (x1, y1, x2, y2), c, k in zip(xyxy, conf, cls):
            out.append(Detection((float(x1), float(y1), float(x2), float(y2)),
                                 float(c), int(k)))
        return out
