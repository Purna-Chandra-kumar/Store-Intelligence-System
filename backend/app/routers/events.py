from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import EventRow
from ..schemas import EventOut


router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventOut])
async def list_events(
    s: AsyncSession = Depends(get_session),
    limit: int = Query(100, ge=1, le=1000),
    event_type: str | None = None,
    camera_id: str | None = None,
):
    q = select(EventRow).order_by(EventRow.ts.desc()).limit(limit)
    if event_type:
        q = q.where(EventRow.event_type == event_type)
    if camera_id:
        q = q.where(EventRow.camera_id == camera_id)
    rows = (await s.execute(q)).scalars().all()
    return [EventOut(event_id=r.event_id, event_type=r.event_type,
                     timestamp=r.ts, camera_id=r.camera_id,
                     track_id=r.track_id, zone=r.zone,
                     metadata=r.metadata_) for r in rows]
