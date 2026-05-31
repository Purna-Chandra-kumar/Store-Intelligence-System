"""ByteTrack tracker via the `supervision` library.

We expose `update(detections, frame_shape) -> list[Track]` so the rest of
the pipeline never sees supervision types.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import supervision as sv

from .detector import Detection


@dataclass(frozen=True)
class Track:
    track_id: int
    xyxy: tuple[float, float, float, float]
    conf: float

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def foot(self) -> tuple[float, float]:
        """Foot point — better than centroid for floor heatmaps."""
        x1, _, x2, y2 = self.xyxy
        return ((x1 + x2) / 2.0, y2)


class PersonTracker:
    def __init__(self) -> None:
        self._bt = sv.ByteTrack(
            track_activation_threshold=0.5,
            lost_track_buffer=30,
            minimum_matching_threshold=0.8,
            frame_rate=30,
        )

    def update(self, detections: list[Detection]) -> list[Track]:
        if not detections:
            empty = sv.Detections.empty()
            self._bt.update_with_detections(empty)
            return []

        xyxy = np.array([d.xyxy for d in detections], dtype=np.float32)
        conf = np.array([d.conf for d in detections], dtype=np.float32)
        cls = np.array([d.cls for d in detections], dtype=int)

        sv_det = sv.Detections(xyxy=xyxy, confidence=conf, class_id=cls)
        tracked = self._bt.update_with_detections(sv_det)

        out: list[Track] = []
        if tracked.tracker_id is None:
            return out
        for box, tid, c in zip(tracked.xyxy, tracked.tracker_id, tracked.confidence):
            out.append(Track(int(tid),
                             (float(box[0]), float(box[1]),
                              float(box[2]), float(box[3])),
                             float(c)))
        return out
