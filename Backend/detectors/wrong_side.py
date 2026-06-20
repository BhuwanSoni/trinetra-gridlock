"""
wrong_side.py
──────────────────────────────────────────────────────────────
Isolates wrong-side-driving detection from a vehicle's tracked trajectory.

v2 upgrade (Improvement ⑨): confidence is no longer a flat -dot value.
It is now scaled by trajectory length so that a vehicle with 90 points
of history is weighted more heavily than one with only 5 frames.
This prevents short trajectory noise from triggering high-confidence
violations during the first few frames of tracking.

Scaling formula:
  base_conf  = max(0, -dot)          (range 0–1 from dot product)
  traj_scale = min(1.0, traj_len/50) (ramps from 0 to 1 over first 50 pts)
  confidence = base_conf * traj_scale

Usage:
    from wrong_side import check_wrong_side
    result = check_wrong_side(trajectory, road_direction=(1, 0))
"""

MIN_TRAJECTORY_POINTS = 5      # raised from 3 — need more data before deciding
MIN_DISPLACEMENT_PX   = 20     # raised from 15 — ignore micro-jitter
DOT_THRESHOLD         = -0.3   # unchanged — how "against traffic" motion must be
FULL_CONFIDENCE_AT    = 50     # trajectory length at which traj_scale reaches 1.0


def check_wrong_side(trajectory: list, road_direction: tuple = (1, 0)) -> dict:
    """
    Args:
        trajectory:     list of (x, y) centre points, oldest → newest
        road_direction: expected (dx, dy) unit vector for legal traffic flow

    Returns:
        {
          violation:     bool
          travel_vector: tuple | None
          confidence:    float   — trajectory-length-scaled (Improvement ⑨)
          traj_len:      int
          review:        str     — "auto" | "manual" | "rejected"
        }
    """
    traj_len = len(trajectory)

    if traj_len < MIN_TRAJECTORY_POINTS:
        return {"violation": False, "travel_vector": None,
                "confidence": 0.0, "traj_len": traj_len, "review": "rejected"}

    x0, y0 = trajectory[0]
    x1, y1 = trajectory[-1]
    dx, dy  = x1 - x0, y1 - y0
    dist    = (dx ** 2 + dy ** 2) ** 0.5

    if dist < MIN_DISPLACEMENT_PX:
        return {"violation": False, "travel_vector": (dx, dy),
                "confidence": 0.0, "traj_len": traj_len, "review": "rejected"}

    # Normalise travel vector
    tvx, tvy = dx / dist, dy / dist

    # Normalise road direction
    rdx, rdy = road_direction
    rmag     = (rdx ** 2 + rdy ** 2) ** 0.5 or 1.0
    rdx, rdy = rdx / rmag, rdy / rmag

    dot = tvx * rdx + tvy * rdy    # +1 = with traffic, -1 = head-on

    # ⑨ Scale confidence by trajectory length
    base_conf  = max(0.0, -dot)
    traj_scale = min(1.0, traj_len / FULL_CONFIDENCE_AT)
    confidence = round(base_conf * traj_scale, 3)

    violation = dot < DOT_THRESHOLD and traj_scale >= 0.2   # need ≥10 pts

    if not violation:
        review = "rejected"
    elif confidence >= 0.90:
        review = "auto"
    else:
        review = "manual"

    return {
        "violation":     violation,
        "travel_vector": (dx, dy),
        "confidence":    confidence,
        "traj_len":      traj_len,
        "review":        review,
    }