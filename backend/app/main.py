from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .consumer import run_consumer
from .routers import (
    analytics,
    anomalies,
    events,
    health,
    heatmap,
    stream,
    tracks,
    zones,
)
from .ws import ws_handler


logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(run_consumer(), name="redis-consumer")
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title="Store Intelligence API",
    version="1.1.0",
    description=(
        "Real-time retail vision analytics — events, zones, queues, anomalies, "
        "and a server-rendered live CCTV MJPEG stream."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(events.router)
app.include_router(zones.router)
app.include_router(analytics.router)
app.include_router(anomalies.router)
app.include_router(heatmap.router)
app.include_router(tracks.router)
app.include_router(stream.router)


@app.websocket("/ws/events")
async def ws_events(ws: WebSocket):
    await ws_handler(ws)
