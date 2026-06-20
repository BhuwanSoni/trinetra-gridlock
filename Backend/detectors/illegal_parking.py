"""
illegal_parking.py
──────────────────────────────────────────────────────────────
Isolates illegal-parking detection as a standalone, independently
testable check.  Mirrors the rule_engine.evaluate_car() parking logic
but is importable by the FastAPI layer or unit tests without pulling
in the full rule engine.

v2 upgrade: STATIONARY_FRAMES_THRESHOLD raised 30 → 120 frames (~4 s at
30 fps).  The old threshold of 30 frames (~1 s) was far too short — it
fired on vehicles waiting at red lights or momentarily stopped in traffic,
causing a high false-positive rate.

Usage:
    from illegal_parking import check_illegal_parking
    result = check_illegal_parking(img, vehicle_box,
                                    stationary=True, frames_stationary=130)
"""

from detector import parking_pipeline, vehicle_outside_parking_zones

# Raised 30 → 120 (~4 s @ 30 fps) to avoid false positives on traffic stops
STATIONARY_FRAMES_THRESHOLD = 120


def check_illegal_parking(img,
                          vehicle_box:        list,
                          stationary:         bool = False,
                          frames_stationary:  int  = 0) -> dict:
    """
    Args:
        img:                full BGR frame
        vehicle_box:        [x1, y1, x2, y2] of the vehicle
        stationary:         True if tracker confirms vehicle is not moving
        frames_stationary:  consecutive stationary frame count from tracker

    Returns:
        {
          violation:    bool
          reason:       str
          parking_dets: list  — detected legal parking-zone boxes in frame
          review:       str   — "auto" | "manual" | "rejected"
        }
    """
    parking_data = parking_pipeline(img)
    zones        = parking_data["parking_zone_boxes"]

    if not stationary or frames_stationary < STATIONARY_FRAMES_THRESHOLD:
        return {
            "violation":    False,
            "reason":       "vehicle not parked long enough",
            "parking_dets": zones,
            "review":       "rejected",
        }

    outside = vehicle_outside_parking_zones(vehicle_box, zones)
    if outside and zones:
        return {
            "violation":    True,
            "reason":       "stationary outside marked zone",
            "parking_dets": zones,
            "review":       "auto",   # stationary + outside zone = unambiguous
        }

    return {
        "violation":    False,
        "reason":       "inside a marked zone or no zones detected",
        "parking_dets": zones,
        "review":       "rejected",
    }