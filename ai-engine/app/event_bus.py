"""Redis Streams publisher.

We use Redis Streams (not pub/sub) because we need:
  * persistence across consumer restarts
  * consumer groups (multiple backend replicas can share load)
  * replay from a known offset for backfill

The publisher API is intentionally narrow — one method, `publish(event)`.
Swapping to Kafka means re-implementing this file only; see
`streaming/README.md`.
"""
from __future__ import annotations

import json
import logging

import redis

from .config import settings
from .schemas import Event


log = logging.getLogger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._r = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )
        self._stream = settings.event_stream
        # cap stream growth at ~1M events; tune in prod.
        self._maxlen = 1_000_000

    def publish(self, event: Event) -> None:
        payload = event.model_dump_json()
        try:
            self._r.xadd(
                self._stream,
                {"data": payload},
                maxlen=self._maxlen,
                approximate=True,
            )
        except redis.RedisError:
            log.exception("Failed to publish event %s", event.event_id)
