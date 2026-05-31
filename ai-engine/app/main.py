"""ai-engine entrypoint.

Owns the per-frame loop:
  read frame → detect → track → zones → queues → anomalies → heatmap → 
  render → encode → publish-to-redis → publish-events

The loop is single-threaded by design. Vision workloads are CPU/GPU bound,
not IO bound; multithreading buys nothing and complicates ordering.
Horizontal scaling is one ai-engine *process per camera* — see
`docs/SCALING.md`.
"""
from __future__ import annotations

import logging
import signal
import sys
import time
from pathlib import Path

import cv2
import redis

from .anomaly import AnomalyEngine
from .config import settings
from .detector import PersonDetector
from .event_bus import EventBus
from .frame_renderer import encode_jpeg, render_frame
from .heatmap import HeatmapAccumulator
from .queue_detector import QueueDetector
from .schemas import Event
from .tracker import PersonTracker
from .zones import ZoneEngine


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("ai-engine")


_running = True


def _stop(*_):
    global _running
    _running = False


def _open_capture(source: str) -> cv2.VideoCapture:
    if source.isdigit():
        cap = cv2.VideoCapture(int(source))
    else:
        cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source: {source}")
    return cap


def main() -> int:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    source = settings.video_source
    camera_id = settings.camera_id
    log.info("Starting ai-engine for camera: %s", camera_id)
    log.info("Video source: %s", source)
    
    if not source.startswith("rtsp://") and not Path(source).exists():
        log.error("Video source %s not found. Run scripts/download_sample_video.sh", source)
        return 2

    cap = _open_capture(source)
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    stride = max(1, int(round(src_fps / settings.target_fps)))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    log.info(
        "Opened %s @ %.1f fps (%dx%d), stride=%d, target_fps=%d",
        source, src_fps, w, h, stride, settings.target_fps
    )
    
    if w <= 0 or h <= 0:
        log.error("Invalid frame dimensions: %dx%d", w, h)
        cap.release()
        return 1

    detector = PersonDetector()
    tracker = PersonTracker()
    zones = ZoneEngine(w, h)
    queues = QueueDetector(zones)
    anomalies = AnomalyEngine()
    heatmap = HeatmapAccumulator(w, h)
    bus = EventBus()
    
    # Connect to Redis for frame publishing
    redis_client = None
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=False,  # We're storing bytes (JPEG)
        )
        redis_client.ping()
        log.info("Connected to Redis at %s:%d", settings.redis_host, settings.redis_port)
    except redis.ConnectionError as e:
        log.error("Failed to connect to Redis: %s", e)
        cap.release()
        return 1

    seen_ids: set[int] = set()
    frame_idx = 0
    last_stats_ts = 0.0
    last_tick = time.time()
    frame_times: list[float] = []  # For FPS calculation
    max_fps_window = 30
    frame_errors = 0
    max_frame_errors = 10

    log.info("Starting main processing loop for camera %s", camera_id)

    while _running:
        ok, frame = cap.read()
        if not ok:
            frame_errors += 1
            if frame_errors % 50 == 0:
                log.warning(
                    "Failed to read frame from %s (error count: %d/%d). Seeking to start.",
                    source, frame_errors, max_frame_errors * 10
                )
            # loop the sample for demo purposes
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        
        frame_idx += 1
        if frame_idx % stride != 0:
            continue
        
        # Validate frame
        if frame is None or frame.size == 0:
            log.error("Invalid frame data at index %d", frame_idx)
            continue
        
        frame_h, frame_w = frame.shape[:2]
        if frame_w != w or frame_h != h:
            log.warning("Frame shape mismatch: expected (%dx%d), got (%dx%d)", w, h, frame_w, frame_h)

        ts = time.time()
        frame_times.append(ts)
        if len(frame_times) > max_fps_window:
            frame_times.pop(0)
        
        # Calculate rolling FPS
        if len(frame_times) > 1:
            fps = len(frame_times) / (frame_times[-1] - frame_times[0] + 1e-6)
        else:
            fps = 0.0

        detections = detector(frame)
        tracks = tracker.update(detections)

        # --- entries to the store (first sighting) ---
        for t in tracks:
            if t.track_id not in seen_ids:
                seen_ids.add(t.track_id)
                bus.publish(Event(event_type="person_entered",
                                  camera_id=settings.camera_id,
                                  track_id=t.track_id,
                                  metadata={"foot": t.foot}))

        # --- zones ---
        entries, exits = zones.update(tracks, ts)
        for t, z in entries:
            bus.publish(Event(event_type="zone_entered",
                              camera_id=settings.camera_id,
                              track_id=t.track_id, zone=z.id,
                              metadata={"zone_name": z.name}))
        for t, z, dwell in exits:
            bus.publish(Event(event_type="zone_exited",
                              camera_id=settings.camera_id,
                              track_id=t.track_id, zone=z.id,
                              metadata={"zone_name": z.name,
                                        "dwell_seconds": round(dwell, 2)}))

        # --- queues ---
        for q in queues.evaluate():
            bus.publish(Event(event_type="queue_detected",
                              camera_id=settings.camera_id,
                              zone=q.zone_id,
                              metadata={"queue_length": q.queue_length,
                                        "wait_seconds": q.wait_seconds}))

        # --- anomalies ---
        for a in anomalies.update(ts, tracks, zones._state):  # noqa: SLF001
            etype = "crowd_detected" if a.kind == "crowd_spike" \
                else "loitering_detected" if a.kind == "loitering" \
                else "anomaly_detected"
            bus.publish(Event(event_type=etype,
                              camera_id=settings.camera_id,
                              track_id=a.track_id, zone=a.zone_id,
                              metadata={"kind": a.kind, "detail": a.detail,
                                        **a.metadata}))

        # --- heatmap accumulate + decay ---
        heatmap.add(tracks)
        now = time.time()
        heatmap.tick(now - last_tick)
        last_tick = now

        # --- periodic frame_stats (every 2s) ---
        if ts - last_stats_ts >= 2.0:
            last_stats_ts = ts
            bus.publish(Event(event_type="frame_stats",
                              camera_id=settings.camera_id,
                              metadata={"live_count": len(tracks),
                                        "occupancy": zones.occupancy(),
                                        "heatmap": heatmap.snapshot(),
                                        "tracks": [
                                            {"id": t.track_id,
                                             "xyxy": list(t.xyxy)}
                                            for t in tracks
                                        ]}))

        # --- RENDER FRAME WITH ANNOTATIONS ---
        try:
            annotated_frame = render_frame(
                frame,
                tracks,
                frame_idx,
                fps,
                len(tracks),
            )
            
            if annotated_frame is None or annotated_frame.size == 0:
                log.error("Rendered frame is invalid at index %d", frame_idx)
                continue
            
            # --- ENCODE TO JPEG ---
            jpeg_bytes = encode_jpeg(annotated_frame, settings.frame_jpeg_quality)
            
            if not jpeg_bytes or len(jpeg_bytes) == 0:
                log.error("JPEG encoding produced empty bytes at frame %d", frame_idx)
                continue
            
            # --- PUBLISH TO REDIS ---
            frame_key = f"{settings.frame_redis_key}:{camera_id}"
            redis_client.setex(
                frame_key,
                settings.frame_ttl_ms // 1000,  # Convert ms to seconds
                jpeg_bytes,
            )
            
            # Log every Nth frame for debugging
            if frame_idx % (stride * 30) == 0:  # ~every 30 processed frames
                log.debug(
                    "[%s] Frame %d published: %d bytes, %dx%d, %.1f fps, %d tracks",
                    camera_id, frame_idx, len(jpeg_bytes), frame_w, frame_h, fps, len(tracks)
                )
            
        except Exception as e:
            log.error("[%s] Failed to render/encode/publish frame %d: %s", 
                     camera_id, frame_idx, e, exc_info=True)

    cap.release()
    if redis_client:
        redis_client.close()
    log.info("[%s] ai-engine stopped cleanly after %d frames", camera_id, frame_idx)
    return 0


if __name__ == "__main__":
    sys.exit(main())

