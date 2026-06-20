"""
red_light.py
──────────────────────────────────────────────────────────────
Isolates red-light-running detection. Uses detector.signal_pipeline()
for signal colour and detector.boxes_overlap() to test whether the
vehicle's box has crossed into the zebra-crossing / stop-line zone
while the light is red.

Distinct from stop_line.py: this only fires when the signal is
actually red. stop_line.py fires on any stop-line/zebra overlap,
regardless of signal colour (e.g. an intersection with a physical
stop line but no working signal).

Usage:
    from red_light import check_red_light
    result = check_red_light(img, vehicle_box)
"""

from detector import signal_pipeline, boxes_overlap

MIN_SIGNAL_CONFIDENCE = 0.4
OVERLAP_THRESHOLD = 0.05   # IoU with the zebra / stop-line box


def check_red_light(img, vehicle_box: list) -> dict:
    """
    Args:
        img:          full BGR frame
        vehicle_box:  [x1, y1, x2, y2] of the vehicle being checked

    Returns:
        {
          violation:    bool
          signal_color: str
          confidence:   float
        }
    """
    sig = signal_pipeline(img)
    is_red = (sig["signal_color"] == "red"
              and sig["signal_conf"] >= MIN_SIGNAL_CONFIDENCE)

    if not is_red:
        return {
            "violation":    False,
            "signal_color": sig["signal_color"],
            "confidence":   sig["signal_conf"],
        }

    crossed_line = any(
        boxes_overlap(vehicle_box, zebra["box"], OVERLAP_THRESHOLD)
        for zebra in sig["zebra_boxes"]
    )

    return {
        "violation":    is_red and crossed_line,
        "signal_color": sig["signal_color"],
        "confidence":   sig["signal_conf"],
    }