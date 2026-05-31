"""Runtime configuration for the ai-engine.

All knobs come from env + YAML. No hard-coded paths in modules.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


CONFIG_DIR = Path(os.getenv("CONFIG_DIR", "/configs"))


def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@dataclass(frozen=True)
class Settings:
    # --- runtime ---
    camera_id: str = os.getenv("CAMERA_ID", "cam-01")
    video_source: str = os.getenv("VIDEO_SOURCE", "/data/sample.mp4")
    target_fps: int = int(os.getenv("TARGET_FPS", "8"))
    device: str = os.getenv("DEVICE", "cpu")

    # --- model ---
    yolo_model: str = os.getenv("YOLO_MODEL", "yolov8n.pt")
    yolo_conf: float = float(os.getenv("YOLO_CONF", "0.35"))

    # --- bus ---
    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    event_stream: str = os.getenv("EVENT_STREAM", "store.events")

    # --- frame publishing to Redis ---
    frame_ttl_ms: int = int(os.getenv("FRAME_TTL_MS", "5000"))
    frame_jpeg_quality: int = int(os.getenv("FRAME_JPEG_QUALITY", "80"))
    frame_redis_key: str = "frame"  # prefix: frame:{camera_id}

    @property
    def zones_cfg(self) -> dict[str, Any]:
        return _load_yaml("zones.yaml")

    @property
    def pipeline_cfg(self) -> dict[str, Any]:
        return _load_yaml("pipeline.yaml").get("pipeline", {})


settings = Settings()
