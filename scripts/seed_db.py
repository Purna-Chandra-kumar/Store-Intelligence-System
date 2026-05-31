"""Seed Postgres with a small amount of synthetic data for UI screenshots
without running the ai-engine. Run after compose is up:

    docker compose exec backend python -m scripts.seed_db
"""
from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from app.db import SessionLocal
from app.models import AnomalyRow, EventRow, HeatmapRow, ZoneMetricRow


async def main() -> None:
    now = datetime.now(timezone.utc)
    async with SessionLocal() as s:
        for i in range(200):
            ts = now - timedelta(minutes=random.randint(0, 24 * 60))
            s.add(EventRow(event_id=str(uuid.uuid4()),
                           event_type="person_entered",
                           ts=ts, camera_id="cam-01",
                           track_id=random.randint(1, 800),
                           zone=None, metadata_={}))
        for zid in ("entrance", "checkout", "makeup", "skincare"):
            s.add(ZoneMetricRow(ts=now, camera_id="cam-01",
                                zone=zid, occupancy=random.randint(0, 12)))
        s.add(AnomalyRow(ts=now, camera_id="cam-01", kind="crowd_spike",
                         detail="Demo anomaly", metadata_={"demo": True}))
        s.add(HeatmapRow(ts=now, camera_id="cam-01",
                         cols=8, rows=4,
                         grid={"cols": 8, "rows": 4,
                               "values": [random.random() for _ in range(32)]}))
        await s.commit()
    print("seeded")


if __name__ == "__main__":
    asyncio.run(main())
