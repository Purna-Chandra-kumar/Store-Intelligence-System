"""Background consumer — pulls from Redis Streams, materializes to Postgres,
and fans out to WebSocket subscribers.

Why one consumer in the backend process (vs a separate worker service)?
  * One less container in dev.
  * The WebSocket fan-out needs the same hot stream anyway.
  * For prod horizontal scaling, run N backend replicas — the consumer-group
    semantics of Redis Streams partition delivery automatically.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

import redis.asyncio as aioredis
from sqlalchemy import insert

from .config import settings
from .db import SessionLocal
from .models import (AnomalyRow, EventRow, HeatmapRow, QueueMetricRow,
                     TrackRow, ZoneMetricRow)
from .ws import broadcaster


log = logging.getLogger("consumer")


async def _ensure_group(r: aioredis.Redis) -> None:
    try:
        await r.xgroup_create(settings.event_stream, settings.consumer_group,
                              id="0", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


async def _persist(event: dict) -> None:
    et = event["event_type"]
    ts = datetime.fromisoformat(event["timestamp"])
    md = event.get("metadata", {}) or {}

    async with SessionLocal() as s:
        # raw event row — universal log
        await s.execute(insert(EventRow).values(
            event_id=event["event_id"], event_type=et, ts=ts,
            camera_id=event["camera_id"], track_id=event.get("track_id"),
            zone=event.get("zone"), metadata_=md,
        ).prefix_with("OR IGNORE", dialect="sqlite")  # no-op on pg, harmless
        )

        if et == "frame_stats":
            occ = md.get("occupancy", {}) or {}
            for zid, n in occ.items():
                await s.execute(insert(ZoneMetricRow).values(
                    ts=ts, camera_id=event["camera_id"], zone=zid,
                    occupancy=int(n), avg_dwell_s=None))
            hm = md.get("heatmap")
            if hm:
                await s.execute(insert(HeatmapRow).values(
                    ts=ts, camera_id=event["camera_id"],
                    cols=hm["cols"], rows=hm["rows"], grid=hm))
            for tr in md.get("tracks", []):
                # upsert-like: insert or update last_seen
                await s.merge(TrackRow(
                    track_id=int(tr["id"]), camera_id=event["camera_id"],
                    first_seen=ts, last_seen=ts,
                    path=[tr.get("xyxy")]))
        elif et == "queue_detected":
            await s.execute(insert(QueueMetricRow).values(
                ts=ts, camera_id=event["camera_id"], zone=event.get("zone") or "",
                queue_length=int(md.get("queue_length", 0)),
                wait_seconds=int(md.get("wait_seconds", 0))))
        elif et in ("crowd_detected", "loitering_detected", "anomaly_detected"):
            await s.execute(insert(AnomalyRow).values(
                ts=ts, camera_id=event["camera_id"],
                kind=md.get("kind", et.replace("_detected", "")),
                track_id=event.get("track_id"), zone=event.get("zone"),
                detail=md.get("detail"), metadata_=md))

        await s.commit()


async def run_consumer() -> None:
    r = aioredis.Redis(host=settings.redis_host, port=settings.redis_port,
                       decode_responses=True)
    await _ensure_group(r)
    consumer_name = f"backend-{id(asyncio.current_task())}"
    log.info("Consumer %s attached to %s/%s",
             consumer_name, settings.event_stream, settings.consumer_group)

    while True:
        try:
            resp = await r.xreadgroup(
                settings.consumer_group, consumer_name,
                streams={settings.event_stream: ">"},
                count=64, block=2000,
            )
        except aioredis.RedisError:
            log.exception("xreadgroup failed; backing off")
            await asyncio.sleep(1.0)
            continue

        if not resp:
            continue
        for _stream, messages in resp:
            for msg_id, fields in messages:
                try:
                    event = json.loads(fields["data"])
                    await _persist(event)
                    await broadcaster.publish(event)
                except Exception:
                    log.exception("Failed to handle %s", msg_id)
                finally:
                    await r.xack(settings.event_stream,
                                 settings.consumer_group, msg_id)
