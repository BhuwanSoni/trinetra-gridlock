"""
helmet_detector.py
──────────────────────────────────────────────────────────────
Isolates the helmet check from detector.bike_pipeline().

v2 upgrade: this module's threshold (0.35) is intentionally close to the
raw model floor. rule_engine.MIN_CONFIDENCE (now 0.40, see bugfix note in
rule_engine.py) is the single source of truth for the *post-fusion* floor
used by the live pipeline; this module's MIN_CONFIDENCE only gates the
standalone /check/helmet endpoint, which runs on raw model_conf with no
scene-confidence fusion applied.

Currently rule_engine.evaluate_bike() reads b_data["helmet"] / b_data["helmet_conf"]
(already produced by bike_pipeline) — no duplicate inference.
This module remains the go-to for:
  • FastAPI /check/helmet endpoint
  • Unit tests for the helmet check in isolation
"""

from detectors.detector import bike_pipeline

HELMET_VIOLATION_LABEL = "no_helmet"
MIN_CONFIDENCE = 0.35          # raised from 0.40 to match rule_engine floor


def check_helmet(img, bike_box: list) -> dict:
    """
    Run the helmet check on a single motorcycle ROI.

    Args:
        img:      full BGR frame
        bike_box: [x1, y1, x2, y2] of the motorcycle

    Returns:
        {
          violation:  bool   — True if rider has no helmet above threshold
          status:     str    — "helmet" | "no_helmet" | "unknown"
          confidence: float
          review:     str    — "auto" | "manual" | "rejected"
        }
    """
    data = bike_pipeline(img, bike_box)
    if not data:
        return {"violation": False, "status": "unknown",
                "confidence": 0.0, "review": "rejected"}

    status    = data.get("helmet", "unknown")
    conf      = data.get("helmet_conf", 0.0)
    violation = status == HELMET_VIOLATION_LABEL and conf >= MIN_CONFIDENCE

    if not violation:
        review = "rejected"
    elif conf >= 0.83:    # matches VIOLATION_CHALLAN_THRESHOLDS["Helmet Violation"]
        review = "auto"
    else:
        review = "manual"

    return {
        "violation":  violation,
        "status":     status,
        "confidence": conf,
        "review":     review,
    }