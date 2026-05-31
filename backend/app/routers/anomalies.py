from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import AnomalyRow
from ..schemas import AnomalyOut


router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("", response_model=list[AnomalyOut])
async def list_anomalies(s: AsyncSession = Depends(get_session),
                         limit: int = Query(100, ge=1, le=1000),
                         kind: str | None = None):
    q = select(AnomalyRow).order_by(AnomalyRow.ts.desc()).limit(limit)
    if kind:
        q = q.where(AnomalyRow.kind == kind)
    rows = (await s.execute(q)).scalars().all()
    return [AnomalyOut(id=r.id, ts=r.ts, kind=r.kind, zone=r.zone,
                       track_id=r.track_id, detail=r.detail,
                       metadata=r.metadata_) for r in rows]
