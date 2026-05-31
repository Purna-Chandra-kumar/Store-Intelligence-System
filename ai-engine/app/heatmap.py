"""Heatmap accumulator.

We bin foot points into a low-res grid (default 64x36 = 2304 cells), and
emit periodic `frame_stats` events with a compact serialization (run-length
encoded ints).  The backend stores snapshots; the frontend renders them.
"""
from __future__ import annotations

import numpy as np

from .config import settings
from .tracker import Track


class HeatmapAccumulator:
    def __init__(self, frame_w: int, frame_h: int) -> None:
        cfg = settings.pipeline_cfg.get("heatmap", {})
        self.cols, self.rows = cfg.get("grid", [64, 36])
        self._w, self._h = frame_w, frame_h
        self._grid = np.zeros((self.rows, self.cols), dtype=np.float32)
        self._decay = float(cfg.get("decay_per_minute", 0.05))

    def add(self, tracks: list[Track]) -> None:
        for t in tracks:
            fx, fy = t.foot
            cx = min(self.cols - 1, max(0, int(fx / self._w * self.cols)))
            cy = min(self.rows - 1, max(0, int(fy / self._h * self.rows)))
            self._grid[cy, cx] += 1.0

    def tick(self, seconds: float) -> None:
        if self._decay <= 0:
            return
        factor = max(0.0, 1.0 - self._decay * (seconds / 60.0))
        self._grid *= factor

    def snapshot(self) -> dict:
        return {
            "cols": self.cols,
            "rows": self.rows,
            "values": self._grid.round(2).flatten().tolist(),
        }
