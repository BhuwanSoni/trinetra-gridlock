"""
stop_line.py
──────────────────────────────────────────────────────────────
Isolates the stop-line / zebra-crossing violation — fires whenever
a vehicle's box overlaps the zebra-crossing zone at all, regardless
of signal colour. Useful for intersections with a physical stop
line but no working / detected signal (see red_light.py for the
signal-gated version).

Usage:
    from stop_line import check_stop_line
    result = check_stop_line(img, vehicle_box)
"""

from detector import signal_pipeline, boxes_overlap

OVERLAP_THRESHOLD = 0.05


def check_stop_line(img, vehicle_box: list) -> dict:
    """
    Args:
        img:          full BGR frame
        vehicle_box:  [x1, y1, x2, y2] of the vehicle being checked

    Returns:
        {
          violation:   bool
          zebra_boxes: list  — detected zebra-crossing boxes in frame
        }
    """
    sig = signal_pipeline(img)
    zebra_boxes = sig["zebra_boxes"]

    if not zebra_boxes:
        return {"violation": False, "zebra_boxes": []}

    crossed = any(
        boxes_overlap(vehicle_box, z["box"], OVERLAP_THRESHOLD)
        for z in zebra_boxes
    )
    return {"violation": crossed, "zebra_boxes": zebra_boxes}