"""In-process WebSocket fan-out.

Single Broadcaster instance. Each connected client gets an asyncio.Queue.
Slow clients are dropped after their queue exceeds `MAX_QUEUE`.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket


log = logging.getLogger("ws")
MAX_QUEUE = 500


class Broadcaster:
    def __init__(self) -> None:
        self._clients: set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def register(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE)
        async with self._lock:
            self._clients.add(q)
        return q

    async def unregister(self, q: asyncio.Queue) -> None:
        async with self._lock:
            self._clients.discard(q)

    async def publish(self, event: dict[str, Any]) -> None:
        dead: list[asyncio.Queue] = []
        for q in list(self._clients):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
                log.warning("Dropping slow WS client")
        for q in dead:
            await self.unregister(q)


broadcaster = Broadcaster()


async def ws_handler(ws: WebSocket) -> None:
    await ws.accept()
    q = await broadcaster.register()
    try:
        while True:
            event = await q.get()
            await ws.send_text(json.dumps(event))
    except Exception:
        pass
    finally:
        await broadcaster.unregister(q)
