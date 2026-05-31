from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..db import get_session
from ..models import ZoneMetricRow
from ..schemas import ZoneOut


router = APIRouter(prefix="/zones", tags=["zones"])


@router.get("", response_model=list[ZoneOut])
async def list_zones(s: AsyncSession = Depends(get_session)):
    cfg = settings.zones()
    out: list[ZoneOut] = []
    cams = cfg.get("cameras", {})
    for _cam, ccfg in cams.items():
        for z in ccfg.get("zones", []):
            # most recent zone metric
            row = (await s.execute(
                select(ZoneMetricRow)
                .where(ZoneMetricRow.zone == z["id"])
                .order_by(ZoneMetricRow.ts.desc())
                .limit(1))).scalar_one_or_none()
            out.append(ZoneOut(
                id=z["id"], name=z["name"],
                type=z.get("type", "standard"),
                occupancy=row.occupancy if row else 0,
                avg_dwell_s=float(row.avg_dwell_s) if row and row.avg_dwell_s else None,
            ))
    return out
