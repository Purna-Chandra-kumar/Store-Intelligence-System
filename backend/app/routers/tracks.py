from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import TrackRow


router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("/{track_id}")
async def get_track(track_id: int, camera_id: str = "cam-01",
                    s: AsyncSession = Depends(get_session)):
    row = (await s.execute(
        select(TrackRow).where(TrackRow.track_id == track_id,
                               TrackRow.camera_id == camera_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Track not found")
    return {"track_id": row.track_id, "camera_id": row.camera_id,
            "first_seen": row.first_seen, "last_seen": row.last_seen,
            "path": row.path}
