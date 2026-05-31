from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import EventRow
from ..schemas import HourlyBucket, LiveCountOut


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/live-count", response_model=LiveCountOut)
async def live_count(camera_id: str = "cam-01",
                     s: AsyncSession = Depends(get_session)):
    # Newest frame_stats event holds authoritative live count.
    row = (await s.execute(
        select(EventRow)
        .where(EventRow.camera_id == camera_id,
               EventRow.event_type == "frame_stats")
        .order_by(EventRow.ts.desc()).limit(1))).scalar_one_or_none()
    n = int((row.metadata_ or {}).get("live_count", 0)) if row else 0
    return LiveCountOut(camera_id=camera_id, live_count=n,
                        updated_at=row.ts if row else datetime.now(timezone.utc))


async def _bucketed(s: AsyncSession, trunc: str, since: datetime):
    bucket = func.date_trunc(trunc, EventRow.ts).label("bucket")
    q = (select(bucket, func.count().label("c"))
         .where(EventRow.event_type == "person_entered",
                EventRow.ts >= since)
         .group_by(bucket).order_by(bucket))
    rows = (await s.execute(q)).all()
    return [HourlyBucket(bucket=r.bucket, count=int(r.c)) for r in rows]


@router.get("/hourly", response_model=list[HourlyBucket])
async def hourly(s: AsyncSession = Depends(get_session)):
    return await _bucketed(s, "hour", datetime.now(timezone.utc) - timedelta(hours=24))


@router.get("/daily", response_model=list[HourlyBucket])
async def daily(s: AsyncSession = Depends(get_session)):
    return await _bucketed(s, "day", datetime.now(timezone.utc) - timedelta(days=30))


@router.get("/explain")
async def explain(camera_id: str = "cam-01",
                  s: AsyncSession = Depends(get_session)):
    """Natural-language summary of the last 15 minutes.

    Deterministic rule-based summarizer — no LLM dependency. Easy to swap
    for one. See `docs/TRADEOFFS.md`.
    """
    since = datetime.now(timezone.utc) - timedelta(minutes=15)
    rows = (await s.execute(
        select(EventRow.event_type, func.count())
        .where(EventRow.ts >= since, EventRow.camera_id == camera_id)
        .group_by(EventRow.event_type))).all()
    counts = {r[0]: int(r[1]) for r in rows}
    n = counts.get("person_entered", 0)
    crowd = counts.get("crowd_detected", 0)
    loiter = counts.get("loitering_detected", 0)
    queues = counts.get("queue_detected", 0)
    parts = [f"In the last 15 min, {n} distinct customers were tracked."]
    if queues:
        parts.append(f"Checkout queues triggered {queues} times.")
    if crowd:
        parts.append(f"{crowd} crowd-spike anomalies were raised.")
    if loiter:
        parts.append(f"{loiter} loitering events flagged for review.")
    if len(parts) == 1:
        parts.append("Store operating within normal parameters.")
    return {"summary": " ".join(parts), "counts": counts}
