"""MJPEG live stream router.

The ai-engine annotates frames (YOLO bboxes, track IDs, HUD with live
people count) and pushes JPEGs to Redis under `frame:{camera_id}`. This
router pulls the latest frame and serves it as a `multipart/x-mixed-replace`
MJPEG stream that any <img src="..."> tag can render.

Endpoints (visible in /docs):
  GET /stream/cameras            list known cameras + live status
  GET /stream/{camera_id}        MJPEG stream
  GET /stream/{camera_id}/snapshot  single annotated JPEG (PNG fallback)
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import redis.asyncio as aioredis
import yaml
from fastapi import APIRouter, HTTPException, Path as PathParam
from fastapi.responses import Response, StreamingResponse

from ..config import settings


log = logging.getLogger("stream")

router = APIRouter(prefix="/stream", tags=["stream"])

BOUNDARY = "frame"
FRAME_TTL_MS = 5_000
POLL_INTERVAL_S = 0.05          # 20 Hz polling
KEEPALIVE_INTERVAL_S = 2.0      # send placeholder if engine is silent

# 1x1 black JPEG fallback when the engine has not produced a frame yet
_BLACK_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707"
    "070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c"
    "1c2837292c30313434341f27393d38323c2e333432ffdb0043010909090c0b0c180d"
    "0d1832211c213232323232323232323232323232323232323232323232323232323232"
    "32323232323232323232323232323232323232323232ffc00011080001000103012200"
    "021101031101ffc4001f0000010501010101010100000000000000000102030405060708"
    "090a0bffc400b5100002010303020403050504040000017d010203000411051221314106"
    "13516107227114328191a1082342b1c11552d1f02433627282090a161718191a25262728"
    "292a3435363738393a434445464748494a535455565758595a636465666768696a737475"
    "767778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6"
    "b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4"
    "f5f6f7f8f9faffc4001f0100030101010101010101010000000000000102030405060708"
    "090a0bffc400b51100020102040403040705040400010277000102031104052131061241"
    "510761711322328108144291a1b1c109233352f0156272d10a162434e125f11718191a26"
    "2728292a35363738393a434445464748494a535455565758595a636465666768696a7374"
    "75767778797a82838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4"
    "b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4"
    "f5f6f7f8f9faffda000c03010002110311003f00fbfcafffd9"
)


def _camera_keys(camera_id: str) -> tuple[str, str]:
    return f"frame:{camera_id}", f"frame:{camera_id}:meta"


async def _redis() -> aioredis.Redis:
    """Create async Redis connection with error handling."""
    try:
        r = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            socket_connect_timeout=5.0,
            socket_keepalive=True,
        )
        await r.ping()
        return r
    except Exception as e:
        log.error("Failed to connect to Redis: %s", e)
        raise


def _load_cameras() -> list[dict[str, Any]]:
    p = Path(settings.config_dir) / "cameras.yaml"
    if not p.exists():
        return [{"id": "cam-01", "name": "Main Floor", "location": "Ground Floor"}]
    data = yaml.safe_load(p.read_text()) or {}
    return list(data.get("cameras", []))


def _multipart_chunk(jpeg: bytes) -> bytes:
    return (
        f"--{BOUNDARY}\r\n"
        f"Content-Type: image/jpeg\r\n"
        f"Content-Length: {len(jpeg)}\r\n\r\n"
    ).encode("ascii") + jpeg + b"\r\n"


@router.get(
    "/cameras",
    summary="List available cameras and live status",
    response_description="Array of cameras with live=true if a recent frame is in Redis.",
)
async def list_cameras() -> dict[str, Any]:
    r = None
    try:
        r = await _redis()
        cams = _load_cameras()
        out: list[dict[str, Any]] = []
        for c in cams:
            cid = c.get("id", "cam-01")
            key, meta_key = _camera_keys(cid)
            try:
                exists = await r.exists(key)
                meta_raw = await r.get(meta_key)
                meta = json.loads(meta_raw) if meta_raw else None
                out.append({
                    **c,
                    "live": bool(exists),
                    "meta": meta,
                    "stream_url": f"/stream/{cid}",
                    "snapshot_url": f"/stream/{cid}/snapshot",
                })
            except Exception as e:
                log.error("Failed to check camera %s: %s", cid, e)
                out.append({
                    **c,
                    "live": False,
                    "meta": None,
                    "stream_url": f"/stream/{cid}",
                    "snapshot_url": f"/stream/{cid}/snapshot",
                })
        return {"cameras": out}
    except Exception as e:
        log.error("list_cameras failed: %s", e)
        # Fallback: return minimal camera list without live status
        cams = _load_cameras()
        return {
            "cameras": [
                {
                    **c,
                    "live": False,
                    "meta": None,
                    "stream_url": f"/stream/{c.get('id', 'cam-01')}",
                    "snapshot_url": f"/stream/{c.get('id', 'cam-01')}/snapshot",
                }
                for c in cams
            ]
        }
    finally:
        if r:
            await r.aclose()


@router.get(
    "/{camera_id}/snapshot",
    summary="Single annotated JPEG snapshot for a camera",
    responses={200: {"content": {"image/jpeg": {}}}},
)
async def snapshot(
    camera_id: str = PathParam(..., examples=["cam-01"]),
) -> Response:
    r = None
    try:
        r = await _redis()
        key, _ = _camera_keys(camera_id)
        jpeg = await r.get(key)
        if not jpeg:
            log.warning("No live frame for camera %s in Redis", camera_id)
            raise HTTPException(
                status_code=404,
                detail=f"No live frame for {camera_id}. AI engine may not be running.",
            )
        log.debug("Snapshot retrieved for %s: %d bytes", camera_id, len(jpeg))
        return Response(
            content=jpeg,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-store"},
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error("snapshot failed for %s: %s", camera_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve snapshot: {e}")
    finally:
        if r:
            await r.aclose()


@router.get(
    "/{camera_id}",
    summary="Live MJPEG stream of annotated CCTV frames",
    description=(
        "Server-rendered live video with YOLOv8 bounding boxes, ByteTrack IDs, "
        "and a HUD showing the live people count. Open in a browser tab or use "
        "as `<img src=\"/stream/cam-01\">`."
    ),
    responses={200: {"content": {"multipart/x-mixed-replace": {}}}},
)
async def mjpeg_stream(
    camera_id: str = PathParam(..., examples=["cam-01"]),
) -> StreamingResponse:
    key, _ = _camera_keys(camera_id)
    log.info("Starting MJPEG stream for camera %s (Redis key: %s)", camera_id, key)

    async def gen():
        r = None
        last_payload: bytes | None = None
        last_send = 0.0
        frame_count = 0
        
        try:
            r = await _redis()
            
            while True:
                try:
                    jpeg = await r.get(key)
                    
                    if jpeg and jpeg != last_payload:
                        # New frame from AI engine
                        last_payload = jpeg
                        last_send = asyncio.get_event_loop().time()
                        frame_count += 1
                        log.debug(
                            "Streaming frame %d for %s (%d bytes)",
                            frame_count,
                            camera_id,
                            len(jpeg),
                        )
                        yield _multipart_chunk(jpeg)
                    else:
                        # No new frame yet, but keep connection alive
                        now = asyncio.get_event_loop().time()
                        if now - last_send > KEEPALIVE_INTERVAL_S:
                            last_send = now
                            if last_payload is None:
                                log.debug(
                                    "Sending keepalive (no frame yet) for %s",
                                    camera_id,
                                )
                            yield _multipart_chunk(last_payload or _BLACK_JPEG)
                    
                    await asyncio.sleep(POLL_INTERVAL_S)
                    
                except asyncio.CancelledError:
                    log.info("Stream for %s cancelled by client", camera_id)
                    return
                except Exception as e:
                    log.error("Error in stream loop for %s: %s", camera_id, e)
                    raise
                    
        except asyncio.CancelledError:
            log.info("Stream generator cancelled for %s", camera_id)
            return
        except Exception as e:
            log.error("Fatal error in MJPEG stream for %s: %s", camera_id, e)
            raise
        finally:
            if r:
                await r.aclose()
            log.info("Stream ended for %s (served %d frames)", camera_id, frame_count)

    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Connection": "close",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        gen(),
        media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
        headers=headers,
    )
