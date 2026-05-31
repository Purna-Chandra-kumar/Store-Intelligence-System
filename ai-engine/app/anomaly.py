"""Rule-based anomaly detection.

Three rules — fast, explainable, tunable:
  * crowd_spike   — total live count > multiplier * rolling baseline
  * loitering     — single track present in any zone > N seconds
  * stationary    — track foot point hasn't moved > radius for N seconds

Rule-based wins here because every alert is auditable. ML anomaly models
generate alerts no one can defend.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable

from .config import settings
from .tracker import Track


@dataclass
class _TrackTrail:
    last_move_ts: float
    last_pos: tuple[float, float]


@dataclass(frozen=True)
class Anomaly:
    kind: str           # crowd_spike | loitering | stationary
    track_id: int | None
    zone_id: str | None
    detail: str
    metadata: dict


class AnomalyEngine:
    def __init__(self) -> None:
        cfg = settings.pipeline_cfg.get("anomalies", {})
        self._crowd_window = cfg.get("crowd_spike", {}).get("window_seconds", 30)
        self._crowd_mult = cfg.get("crowd_spike", {}).get("multiplier", 2.5)
        self._loiter_secs = cfg.get("loitering", {}).get("seconds", 180)
        self._stat_radius = cfg.get("stationary", {}).get("px_radius", 40)
        self._stat_secs = cfg.get("stationary", {}).get("seconds", 120)

        # rolling baseline of total live count (per-second samples)
        self._counts: deque[tuple[float, int]] = deque(maxlen=600)
        self._trails: dict[int, _TrackTrail] = {}
        self._fired_loiter: set[tuple[int, str]] = set()
        self._fired_stat: set[int] = set()

    def update(self, ts: float, tracks: list[Track],
               zone_state: dict[int, dict[str, float]]) -> list[Anomaly]:
        anomalies: list[Anomaly] = []
        n_live = len(tracks)

        # --- crowd spike ---
        self._counts.append((ts, n_live))
        cutoff = ts - self._crowd_window
        recent = [c for t, c in self._counts if t >= cutoff]
        baseline = max(1.0, sum(recent) / max(1, len(recent)))
        if n_live > self._crowd_mult * baseline and n_live >= 5:
            anomalies.append(Anomaly(
                "crowd_spike", None, None,
                f"Live count {n_live} > {self._crowd_mult}x baseline {baseline:.1f}",
                {"live_count": n_live, "baseline": baseline}))

        # --- loitering ---
        for tid, zmap in zone_state.items():
            for zid, entered_at in zmap.items():
                if ts - entered_at > self._loiter_secs:
                    key = (tid, zid)
                    if key not in self._fired_loiter:
                        self._fired_loiter.add(key)
                        anomalies.append(Anomaly(
                            "loitering", tid, zid,
                            f"Track {tid} in {zid} for {int(ts-entered_at)}s",
                            {"seconds": int(ts - entered_at)}))

        # --- stationary ---
        live_ids = {t.track_id for t in tracks}
        for t in tracks:
            trail = self._trails.get(t.track_id)
            if trail is None:
                self._trails[t.track_id] = _TrackTrail(ts, t.foot)
                continue
            dx = t.foot[0] - trail.last_pos[0]
            dy = t.foot[1] - trail.last_pos[1]
            if math.hypot(dx, dy) > self._stat_radius:
                trail.last_move_ts = ts
                trail.last_pos = t.foot
                self._fired_stat.discard(t.track_id)
            elif ts - trail.last_move_ts > self._stat_secs \
                    and t.track_id not in self._fired_stat:
                self._fired_stat.add(t.track_id)
                anomalies.append(Anomaly(
                    "stationary", t.track_id, None,
                    f"Track {t.track_id} stationary for {int(ts-trail.last_move_ts)}s",
                    {"seconds": int(ts - trail.last_move_ts)}))

        # gc gone tracks
        for gone in self._trails.keys() - live_ids:
            self._trails.pop(gone, None)
            self._fired_stat.discard(gone)

        return anomalies
