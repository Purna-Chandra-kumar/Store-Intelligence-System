"""Zone engine — polygon containment + per-track entry/exit edge detection.

Zones live in YAML so the same binary serves any store. The engine emits:
  * zone_entered / zone_exited (state edges)
  * dwell time on exit
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from shapely.geometry import Point, Polygon

from .config import settings
from .tracker import Track


@dataclass(frozen=True)
class ZoneDef:
    id: str
    name: str
    type: str                 # gateway | queue | standard
    polygon: Polygon
    dwell_alert_seconds: int = 0
    queue_min_people: int = 0
    queue_seconds_per_person: int = 0


@dataclass
class _TrackZoneState:
    zone_id: str
    entered_at: float


class ZoneEngine:
    def __init__(self, frame_w: int, frame_h: int) -> None:
        self.zones: list[ZoneDef] = self._load(frame_w, frame_h)
        # track_id -> {zone_id: entered_at}
        self._state: dict[int, dict[str, float]] = {}

    @staticmethod
    def _load(w: int, h: int) -> list[ZoneDef]:
        cfg = settings.zones_cfg
        cam_cfg = cfg.get("cameras", {}).get(settings.camera_id, {})
        zones: list[ZoneDef] = []
        for z in cam_cfg.get("zones", []):
            pts = [(p[0] * w, p[1] * h) for p in z["polygon"]]
            q = z.get("queue", {}) or {}
            zones.append(ZoneDef(
                id=z["id"],
                name=z["name"],
                type=z.get("type", "standard"),
                polygon=Polygon(pts),
                dwell_alert_seconds=int(z.get("dwell_alert_seconds", 0)),
                queue_min_people=int(q.get("min_people", 0)),
                queue_seconds_per_person=int(q.get("seconds_per_person", 0)),
            ))
        return zones

    def update(self, tracks: list[Track], ts: float
               ) -> tuple[list[tuple[Track, ZoneDef]],
                          list[tuple[Track, ZoneDef, float]]]:
        """Return (entries, exits_with_dwell)."""
        entries: list[tuple[Track, ZoneDef]] = []
        exits: list[tuple[Track, ZoneDef, float]] = []

        live_ids = {t.track_id for t in tracks}
        # Build current containment for live tracks
        current: dict[int, set[str]] = {}
        for t in tracks:
            p = Point(*t.foot)
            in_zones = {z.id for z in self.zones if z.polygon.contains(p)}
            current[t.track_id] = in_zones

            prev = self._state.setdefault(t.track_id, {})
            for zid in in_zones - prev.keys():
                zdef = self._zone(zid)
                prev[zid] = ts
                entries.append((t, zdef))
            for zid in list(prev.keys() - in_zones):
                zdef = self._zone(zid)
                dwell = ts - prev.pop(zid)
                exits.append((t, zdef, dwell))

        # Tracks that vanished: flush their open zones
        for gone in list(self._state.keys() - live_ids):
            for zid, t0 in self._state.pop(gone).items():
                # Synthesize a minimal Track for the exit payload
                exits.append((Track(gone, (0, 0, 0, 0), 0.0),
                              self._zone(zid), ts - t0))

        return entries, exits

    def occupancy(self) -> dict[str, int]:
        counts: dict[str, int] = {z.id: 0 for z in self.zones}
        for zmap in self._state.values():
            for zid in zmap:
                counts[zid] = counts.get(zid, 0) + 1
        return counts

    def zones_of_type(self, t: str) -> Iterable[ZoneDef]:
        return (z for z in self.zones if z.type == t)

    def _zone(self, zid: str) -> ZoneDef:
        for z in self.zones:
            if z.id == zid:
                return z
        raise KeyError(zid)
