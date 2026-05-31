"""Queue detector — heuristic, deliberately simple, production-tunable.

A queue is declared on any `queue` zone where current occupancy >= min_people.
Wait-time estimate = (queue_length - 1) * seconds_per_person.

The simplicity is the feature: store managers can reason about and tune
the thresholds. ML-based queue regression is a v2 concern.
"""
from __future__ import annotations

from dataclasses import dataclass

from .zones import ZoneDef, ZoneEngine


@dataclass(frozen=True)
class QueueReading:
    zone_id: str
    queue_length: int
    wait_seconds: int


class QueueDetector:
    def __init__(self, zones: ZoneEngine) -> None:
        self._zones = zones

    def evaluate(self) -> list[QueueReading]:
        occ = self._zones.occupancy()
        readings: list[QueueReading] = []
        for z in self._zones.zones_of_type("queue"):
            n = occ.get(z.id, 0)
            if n >= z.queue_min_people:
                wait = max(0, (n - 1) * z.queue_seconds_per_person)
                readings.append(QueueReading(z.id, n, wait))
        return readings
