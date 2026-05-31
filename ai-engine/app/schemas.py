"""Canonical event schema.

Every event produced by the ai-engine conforms to one of these models.
The backend deserializes against the same schemas — keep them in sync via
the `docs/EVENTS.md` reference.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


EventType = Literal[
    "person_entered",
    "person_exited",
    "zone_entered",
    "zone_exited",
    "queue_detected",
    "crowd_detected",
    "loitering_detected",
    "anomaly_detected",
    "frame_stats",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: str = Field(default_factory=_now)
    camera_id: str
    track_id: Optional[int] = None
    zone: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
