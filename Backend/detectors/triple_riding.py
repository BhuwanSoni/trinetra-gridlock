"""
triple_riding.py
──────────────────────────────────────────────────────────────
Isolates the triple-riding check from detector.bike_pipeline().

v2 upgrade: MIN_CONFIDENCE raised 0.40 → 0.65 to match global rule_engine
floor.  Review tier returned so API callers know whether to auto-issue
or queue for human review.

Usage:
    from triple_riding import check_triple_riding
    result = check_triple_riding(img, bike_box)
"""

from detector import bike_pipeline

TRIPLE_RIDING_LABEL = "triple_rider"
MIN_CONFIDENCE      = 0.65     # raised from 0.40
CHALLAN_THRESHOLD   = 0.88     # matches VIOLATION_CHALLAN_THRESHOLDS in rule_engine


def check_triple_riding(img, bike_box: list) -> dict:
    """
    Run the triple-riding check on a single motorcycle ROI.

    Args:
        img:      full BGR frame
        bike_box: [x1, y1, x2, y2] of the motorcycle

    Returns:
        {
          violation:  bool
          status:     str    — "single" | "double" | "triple_rider" | "unknown"
          confidence: float
          review:     str    — "auto" | "manual" | "rejected"
        }
    """
    data = bike_pipeline(img, bike_box)
    if not data:
        return {"violation": False, "status": "unknown",
                "confidence": 0.0, "review": "rejected"}

    status    = data.get("triple_riding", "unknown")
    conf      = data.get("triple_conf",   0.0)
    violation = status == TRIPLE_RIDING_LABEL and conf >= MIN_CONFIDENCE

    if not violation:
        review = "rejected"
    elif conf >= CHALLAN_THRESHOLD:
        review = "auto"
    else:
        review = "manual"

    return {
        "violation":  violation,
        "status":     status,
        "confidence": conf,
        "review":     review,
    }