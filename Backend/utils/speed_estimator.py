"""
speed_estimator.py
──────────────────────────────────────────────────────────────
Feature 2 — Speed Violation Detection

Estimates vehicle speed from DeepSORT trajectories and frame
timestamps, then flags violations against configurable zone limits.

Method:
    speed_kmh = (pixel_distance / pixels_per_metre) / time_seconds × 3.6

Calibration:
    pixels_per_metre is set per camera by measuring a known reference
    distance in the scene (e.g. lane width = 3.5 m).
    Default is 10 px/m which gives reasonable estimates at typical CCTV
    resolutions — tune with CAMERA_CALIBRATION below.

Violation thresholds (km/h):
    School zone     25
    Residential     40
    Urban arterial  60
    Highway         100
    (configure per camera in SPEED_ZONES)
"""

from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

# ── Per-camera calibration ─────────────────────────────────────────────────────
# pixels_per_metre: how many pixels = 1 real-world metre in that camera's view.
# Measure this once per camera using a known ground-plane reference object.

CAMERA_CALIBRATION: dict[str, float] = {
    "CAM-01": 10.0,    # default — tune per deployment
    "CAM-02": 12.5,
    "CAM-03":  9.0,
    "CAM-04": 11.0,
    "CAM-05":  8.5,
    "DEMO-CAM": 10.0,
}

DEFAULT_PPM = 10.0  # pixels per metre fallback

# ── Speed zone limits (km/h) ───────────────────────────────────────────────────

SPEED_ZONES: dict[str, float] = {
    "school":      25.0,
    "residential": 40.0,
    "urban":       60.0,
    "highway":    100.0,
}

DEFAULT_SPEED_LIMIT = 60.0  # urban arterial

# ── Temporal tracking state ────────────────────────────────────────────────────
# track_id → deque of (cx, cy, timestamp_sec)

_track_history: dict[int, deque] = defaultdict(lambda: deque(maxlen=60))

# ── Speed measurement window ───────────────────────────────────────────────────
# Use last N frames of trajectory for a stable average
SPEED_WINDOW_FRAMES = 10


# ── Core dataclass ─────────────────────────────────────────────────────────────

@dataclass
class SpeedMeasurement:
    track_id:       int
    estimated_kmh:  float
    speed_limit:    float
    is_violation:   bool
    excess_kmh:     float
    confidence:     float   # 0-1 based on trajectory length and consistency
    details:        str     = ""

    def to_dict(self) -> dict:
        return {
            "track_id":      self.track_id,
            "estimated_kmh": round(self.estimated_kmh, 1),
            "speed_limit":   self.speed_limit,
            "is_violation":  self.is_violation,
            "excess_kmh":    round(self.excess_kmh, 1),
            "confidence":    round(self.confidence, 3),
            "details":       self.details,
        }


# ── Public API ─────────────────────────────────────────────────────────────────

def record_position(track_id: int, cx: int, cy: int,
                    ts: float = None) -> None:
    """
    Called each time a tracked vehicle appears in a frame.
    ts: UNIX timestamp in seconds (default: now).
    """
    _track_history[track_id].append((cx, cy, ts or time.monotonic()))


def estimate_speed(track_id:    int,
                   camera_id:   str   = "CAM-01",
                   zone:        str   = "urban") -> Optional[SpeedMeasurement]:
    """
    Estimate speed for a track using recent trajectory points.

    Returns SpeedMeasurement or None if insufficient history.
    """
    history = _track_history.get(track_id)
    if not history or len(history) < SPEED_WINDOW_FRAMES:
        return None

    ppm   = CAMERA_CALIBRATION.get(camera_id, DEFAULT_PPM)
    limit = SPEED_ZONES.get(zone, DEFAULT_SPEED_LIMIT)

    # Sliding-window speed samples
    points = list(history)[-SPEED_WINDOW_FRAMES:]
    speeds = []
    for i in range(1, len(points)):
        x0, y0, t0 = points[i - 1]
        x1, y1, t1 = points[i]
        dt = t1 - t0
        if dt <= 0:
            continue
        dist_px = math.hypot(x1 - x0, y1 - y0)
        dist_m  = dist_px / ppm
        kmh     = (dist_m / dt) * 3.6
        speeds.append(kmh)

    if not speeds:
        return None

    avg_kmh = float(sum(speeds) / len(speeds))

    # Confidence: higher with more samples and low variance
    variance   = float(sum((s - avg_kmh) ** 2 for s in speeds) / len(speeds))
    conf = max(0.3, min(0.95, 1.0 - variance / (avg_kmh + 1e-6) * 0.1))
    conf = round(conf * (len(speeds) / SPEED_WINDOW_FRAMES), 3)

    excess  = max(0.0, avg_kmh - limit)
    is_viol = avg_kmh > limit * 1.05   # 5% tolerance

    details = (f"~{avg_kmh:.0f} km/h in {zone} zone "
               f"(limit {limit:.0f}) via {camera_id}")

    return SpeedMeasurement(
        track_id      = track_id,
        estimated_kmh = round(avg_kmh, 1),
        speed_limit   = limit,
        is_violation  = is_viol,
        excess_kmh    = round(excess, 1),
        confidence    = conf,
        details       = details,
    )


def update_and_check(track_id:  int,
                     cx:        int,
                     cy:        int,
                     camera_id: str  = "CAM-01",
                     zone:      str  = "urban",
                     ts:        float = None) -> Optional[SpeedMeasurement]:
    """
    Convenience: record position then immediately return speed estimate.
    Returns None until enough history is accumulated.
    """
    record_position(track_id, cx, cy, ts)
    return estimate_speed(track_id, camera_id, zone)


def reset() -> None:
    """Clear all tracking state between videos."""
    _track_history.clear()


# ── Fine schedule for speed violations ────────────────────────────────────────

def speed_fine(excess_kmh: float) -> int:
    """
    MV Act 2019-style speed fine tiers (INR).
    """
    if excess_kmh <= 0:
        return 0
    if excess_kmh <= 10:
        return 1000
    if excess_kmh <= 20:
        return 2000
    if excess_kmh <= 40:
        return 4000
    return 5000   # > 40 km/h over limit