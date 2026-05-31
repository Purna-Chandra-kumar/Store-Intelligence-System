from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import HeatmapRow
from ..schemas import HeatmapOut


router = APIRouter(prefix="/heatmap", tags=["heatmap"])


@router.get("", response_model=HeatmapOut)
async def latest_heatmap(camera_id: str = "cam-01",
                         s: AsyncSession = Depends(get_session)):
    row = (await s.execute(
        select(HeatmapRow)
        .where(HeatmapRow.camera_id == camera_id)
        .order_by(HeatmapRow.ts.desc()).limit(1))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "No heatmap yet")
    return HeatmapOut(ts=row.ts, cols=row.cols, rows=row.rows, grid=row.grid)
