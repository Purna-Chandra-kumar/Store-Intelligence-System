from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventOut(BaseModel):
    event_id: str
    event_type: str
    timestamp: datetime
    camera_id: str
    track_id: int | None
    zone: str | None
    metadata: dict[str, Any]


class LiveCountOut(BaseModel):
    camera_id: str
    live_count: int
    updated_at: datetime


class ZoneOut(BaseModel):
    id: str
    name: str
    type: str
    occupancy: int
    avg_dwell_s: float | None


class HourlyBucket(BaseModel):
    bucket: datetime
    count: int


class AnomalyOut(BaseModel):
    id: int
    ts: datetime
    kind: str
    zone: str | None
    track_id: int | None
    detail: str | None
    metadata: dict[str, Any]


class HeatmapOut(BaseModel):
    ts: datetime
    cols: int
    rows: int
    grid: dict
