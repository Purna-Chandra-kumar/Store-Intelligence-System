"""Frame rendering and JPEG encoding for live streaming.

Renders:
  * Detection bounding boxes (green)
  * Track IDs with confidence
  * Live people count HUD in top-left corner
  * Frame index and FPS
"""
from __future__ import annotations

import logging

import cv2
import numpy as np

from .tracker import Track


log = logging.getLogger("frame_renderer")

# Color scheme
BOX_COLOR = (0, 255, 0)  # Green in BGR
TEXT_COLOR = (255, 255, 255)  # White in BGR
TEXT_BG_COLOR = (0, 0, 0)  # Black in BGR
HUD_BG_COLOR = (50, 50, 50)  # Dark gray in BGR

# Fonts and sizes
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.6
FONT_THICKNESS = 1
BOX_THICKNESS = 2

# HUD constants
HUD_PADDING = 10
HUD_LINE_HEIGHT = 25
HUD_TEXT_Y_OFFSET = 20


def render_frame(
    frame: np.ndarray,
    tracks: list[Track],
    frame_idx: int,
    fps: float,
    live_count: int,
) -> np.ndarray:
    """Render detections, tracks, and HUD onto frame.
    
    Args:
        frame: Input BGR frame from OpenCV
        tracks: List of Track objects with bounding boxes
        frame_idx: Current frame index
        fps: Estimated FPS
        live_count: Number of live tracks
    
    Returns:
        Annotated BGR frame
    """
    # Validate input
    if frame is None or frame.size == 0:
        log.error("Invalid input frame (None or empty)")
        return frame
    
    if not isinstance(frame, np.ndarray):
        log.error("Frame is not numpy array: %s", type(frame))
        return frame
    
    # Make a copy to avoid modifying original
    try:
        out = frame.copy()
    except Exception as e:
        log.error("Failed to copy frame: %s", e)
        return frame
    
    # Validate frame shape
    if len(out.shape) != 3 or out.shape[2] != 3:
        log.warning("Unexpected frame shape: %s", out.shape)
        return out
    
    h, w = out.shape[:2]
    
    if w <= 0 or h <= 0:
        log.error("Invalid frame dimensions: %dx%d", w, h)
        return out

    try:
        # Draw bounding boxes and track IDs
        for track in tracks:
            try:
                x1, y1, x2, y2 = [int(v) for v in track.xyxy]
                
                # Clamp to frame boundaries
                x1 = max(0, min(x1, w - 1))
                y1 = max(0, min(y1, h - 1))
                x2 = max(0, min(x2, w - 1))
                y2 = max(0, min(y2, h - 1))
                
                if x2 <= x1 or y2 <= y1:
                    continue
                
                # Draw box
                cv2.rectangle(out, (x1, y1), (x2, y2), BOX_COLOR, BOX_THICKNESS)
                
                # Draw track ID with background
                label = f"ID:{track.track_id} {track.conf:.2f}"
                text_size = cv2.getTextSize(label, FONT, FONT_SCALE, FONT_THICKNESS)[0]
                text_x = x1
                text_y = max(y1 - 5, 20)
                
                # Background for text
                cv2.rectangle(
                    out,
                    (text_x, text_y - text_size[1] - 5),
                    (text_x + text_size[0] + 5, text_y + 5),
                    TEXT_BG_COLOR,
                    -1,  # filled
                )
                
                # Text
                cv2.putText(
                    out,
                    label,
                    (text_x + 2, text_y - 2),
                    FONT,
                    FONT_SCALE,
                    TEXT_COLOR,
                    FONT_THICKNESS,
                )
            except Exception as e:
                log.warning("Failed to render track: %s", e)
                continue

        # Draw HUD (top-left corner)
        hud_lines = [
            f"Live: {live_count}",
            f"Frame: {frame_idx}",
            f"FPS: {fps:.1f}",
        ]
        
        # HUD background
        hud_width = 120
        hud_height = len(hud_lines) * HUD_LINE_HEIGHT + HUD_PADDING * 2
        cv2.rectangle(
            out,
            (HUD_PADDING, HUD_PADDING),
            (HUD_PADDING + hud_width, HUD_PADDING + hud_height),
            HUD_BG_COLOR,
            -1,  # filled
        )
        
        # HUD text
        for i, line in enumerate(hud_lines):
            y = HUD_PADDING + HUD_TEXT_Y_OFFSET + i * HUD_LINE_HEIGHT
            cv2.putText(
                out,
                line,
                (HUD_PADDING + 8, y),
                FONT,
                FONT_SCALE,
                TEXT_COLOR,
                FONT_THICKNESS,
            )

    except Exception as e:
        log.error("Error rendering frame: %s", e)
        # Return original frame if rendering fails

    return out


def encode_jpeg(frame: np.ndarray, quality: int = 80) -> bytes:
    """Encode BGR frame to JPEG bytes.
    
    Args:
        frame: BGR frame from OpenCV
        quality: JPEG quality (0-100, default 80)
    
    Returns:
        JPEG bytes
    """
    if frame is None or frame.size == 0:
        log.error("Cannot encode: frame is None or empty")
        return b""
    
    if not isinstance(frame, np.ndarray):
        log.error("Cannot encode: frame is not numpy array")
        return b""
    
    quality = max(0, min(100, quality))  # Clamp quality to 0-100
    
    try:
        ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ret:
            log.error("cv2.imencode failed to encode frame")
            return b""
        
        jpeg_bytes = bytes(buffer)
        if not jpeg_bytes:
            log.error("Encoded JPEG is empty")
            return b""
        
        return jpeg_bytes
    except Exception as e:
        log.error("Failed to encode frame to JPEG: %s", e)
        return b""
