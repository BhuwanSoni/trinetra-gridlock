"""
tracker.py
──────────────────────────────────────────────────────────────
Improvement #1  — Vehicle Tracking (DeepSORT)
Improvement #7  — Wrong-Side Detection via trajectory angle
Improvement #6  — Stationary-vehicle helper for illegal parking

Assigns persistent IDs (Car#17, Bike#22) across frames so the
rule engine can reason about *behaviour over time*, not just
what's visible in a single frame.

Install:
    pip install deep-sort-realtime
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Optional

import numpy as np

# ── DeepSORT (graceful fallback if not installed) ──────────────────────────────

_deepsort_instance = None

PARKING_FRAMES_THRESHOLD = 90    # ~3 s at 30 fps
STATIONARY_PX_THRESHOLD  = 15   # pixels of movement to count as "moving"
WRONG_SIDE_ANGLE_DEG     = 120  # angle vs road direction → wrong side


def _get_tracker():
    global _deepsort_instance
    if _deepsort_instance is None:
        try:
            from deep_sort_realtime.deepsort_tracker import DeepSort
            _deepsort_instance = DeepSort(max_age=30, n_init=3, nn_budget=100)
            print("[Tracker] DeepSORT loaded.")
        except ImportError:
            print("[WARN] deep-sort-realtime not installed → tracking disabled.")
            print("       pip install deep-sort-realtime")
    return _deepsort_instance


# ── Per-track state ────────────────────────────────────────────────────────────

_trajectories: dict[int, deque] = defaultdict(lambda: deque(maxlen=90))
_first_seen:   dict[int, int]   = {}
_frame_counter: int = 0


# ── Public API ─────────────────────────────────────────────────────────────────

def update_tracks(detections: list, img: np.ndarray) -> list:
    """
    Feed current-frame detections into DeepSORT.

    Args:
        detections: list of detector.py dicts
                    {class_name, conf, box:[x1,y1,x2,y2]}
        img:        current BGR frame

    Returns:
        Same list enriched with:
          track_id   – persistent integer (or -1 in fallback mode)
          label      – e.g. "Car#17"
          trajectory – list of (cx, cy) tuples (historical path)
    """
    global _frame_counter
    _frame_counter += 1

    tracker = _get_tracker()
    if tracker is None:
        # Fallback: stable fake IDs by position hash (good enough for image mode)
        for i, d in enumerate(detections):
            d["track_id"]  = i
            d["label"]     = f"{d['class_name'].title()}#{i}"
            d["trajectory"] = []
        return detections

    # Convert to DeepSORT format: ([x, y, w, h], confidence, class_name)
    raw_dets = []
    for d in detections:
        x1, y1, x2, y2 = d["box"]
        raw_dets.append(([x1, y1, x2 - x1, y2 - y1], d["conf"], d["class_name"]))

    tracks = tracker.update_tracks(raw_dets, frame=img)

    enriched: list = []
    for track in tracks:
        if not track.is_confirmed():
            continue

        tid         = track.track_id
        x1, y1, x2, y2 = map(int, track.to_ltrb())
        cx, cy      = (x1 + x2) // 2, (y1 + y2) // 2

        _trajectories[tid].append((cx, cy))
        _first_seen.setdefault(tid, _frame_counter)

        cls_name = track.det_class or "vehicle"
        enriched.append({
            "class_name":  cls_name,
            "conf":        round(track.det_conf or 0.5, 3),
            "box":         [x1, y1, x2, y2],
            "track_id":    tid,
            "label":       f"{cls_name.title()}#{tid}",
            "trajectory":  list(_trajectories[tid]),
        })

    return enriched


# ── Trajectory helpers ─────────────────────────────────────────────────────────

def _direction_vector(trajectory: list) -> Optional[tuple]:
    """Unit vector of motion from last 10 points, or None if insufficient."""
    if len(trajectory) < 10:
        return None
    p0, p1 = trajectory[-10], trajectory[-1]
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    mag = math.hypot(dx, dy)
    return (dx / mag, dy / mag) if mag > 1 else None


def is_wrong_side(trajectory: list,
                  road_direction: tuple = (1, 0)) -> tuple[bool, float]:
    """
    Improvement #7 — trajectory-angle wrong-side detection.

    Args:
        trajectory:     list of (cx, cy) from track history
        road_direction: expected (dx, dy) unit vector for legal flow
                        default (1, 0) = left-to-right

    Returns:
        (is_wrong_side, angle_degrees)
        angle > WRONG_SIDE_ANGLE_DEG  →  vehicle moving against traffic
    """
    vec = _direction_vector(trajectory)
    if vec is None:
        return False, 0.0

    dot   = max(-1.0, min(1.0, vec[0] * road_direction[0] + vec[1] * road_direction[1]))
    angle = math.degrees(math.acos(dot))
    return angle > WRONG_SIDE_ANGLE_DEG, round(angle, 1)


def is_stationary(track_id: int, trajectory: list) -> tuple[bool, int]:
    """
    Improvement #6 — detect vehicles that haven't moved enough to be driving.

    Returns:
        (is_stationary, frames_elapsed_since_first_seen)
    """
    frames_seen = _frame_counter - _first_seen.get(track_id, _frame_counter)

    if len(trajectory) < PARKING_FRAMES_THRESHOLD:
        return False, frames_seen

    recent = trajectory[-PARKING_FRAMES_THRESHOLD:]
    xs = [p[0] for p in recent]
    ys = [p[1] for p in recent]
    spread = math.hypot(max(xs) - min(xs), max(ys) - min(ys))

    return spread < STATIONARY_PX_THRESHOLD, frames_seen


def reset_tracker() -> None:
    """Call between videos / test runs to wipe all tracking state."""
    global _deepsort_instance, _frame_counter
    _deepsort_instance = None
    _trajectories.clear()
    _first_seen.clear()
    _frame_counter = 0