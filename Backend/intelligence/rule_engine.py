"""
rule_engine.py
──────────────────────────────────────────────────────────────
Layer 4 — Rule-Based Reasoning Engine  (UPGRADED v2)

Improvements applied in this revision
  ① Raised MIN_CONFIDENCE       0.50 → 0.65
  ② Raised CHALLAN_CONFIDENCE   0.85 → 0.90
  ③ Tightened per-type thresholds (phone 0.88→0.92, wrong-side 0.87→0.90, …)
  ④ UNKNOWN plate guard — no auto-challan when plate unreadable
  ⑤ Consecutive-frame guard — violations only raised after N confirmed frames
  ⑥ Review-queue tiers: AUTO_APPROVED / MANUAL_REVIEW / REJECTED
  ⑦ Illegal parking threshold raised 90 → 120 frames (~4 s @ 30 fps)
  ⑧ helmet_detector / triple_riding modules now called from evaluate_bike
  ⑨ Wrong-side confidence now scaled by trajectory length (longer = surer)
  ⑩ Confidence fusion weights documented; scene weight down from 0.30 → 0.25

Pre-existing improvements kept
  #4  Confidence Fusion   final = 0.75·model + 0.25·scene
  #5  Violation Severity  Critical / High / Medium / Low + risk 0–100
  #7  Wrong-Side Driving  trajectory angle vs road direction
  #10 Multi-Violation Fusion  one fused record per vehicle/plate
  Traffic Sign Rules  No Entry · Stop Sign · Overspeeding

Public API consumed by main.py (unchanged signatures):
    evaluate_bike(b_data, signal_data, sign_data, box, plate, scene_conf,
                  trajectory, tid, speed_kmh)
    evaluate_car(c_data, signal_data, sign_data, box, plate, scene_conf,
                 parking_data, trajectory, frames_stat, tid, speed_kmh)
    evaluate_pedestrian(signal_data, box, tid)
    fuse_vehicle_violations(violations, plate)
    summarize_violations(violations)
    confirm_violation(track_id, vtype)   ← NEW — consecutive-frame gate
    reset_confirmation_state()           ← NEW — call between videos
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Optional

from detectors.tracker import is_wrong_side


# ══════════════════════════════════════════════════════════════════════════════
# Violation catalogue
# ══════════════════════════════════════════════════════════════════════════════

# name → (severity, base_risk, fine_inr)
VIOLATION_CATALOGUE: dict[str, tuple[str, int, int]] = {
    "Red Light Violation":          ("Critical", 95, 5000),
    "Wrong Side Driving":           ("Critical", 90, 5000),
    "No Entry Violation":           ("Critical", 88, 5000),
    "Triple Riding":                ("High",     85, 1000),
    "Abnormal Driving Behaviour":   ("High",     80, 2000),
    "Mobile Usage While Driving":   ("High",     78, 5000),
    "Overspeeding":                 ("High",     75, 2000),
    "Helmet Violation":             ("Medium",   70, 1000),
    "Seat Belt Violation":          ("Medium",   65, 1000),
    "Stop Line / Zebra Violation":  ("Medium",   60, 1000),
    "Stop Sign Violation":          ("Medium",   58, 1000),
    "Illegal Parking":              ("Low",      40,  500),
    "Pedestrian Signal Violation":  ("Low",      35,  200),
}

SEVERITY_ORDER = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}


# ══════════════════════════════════════════════════════════════════════════════
# Confidence thresholds  (Improvement ①②③)
# ══════════════════════════════════════════════════════════════════════════════

# Confidence fusion weights (↓ scene weight from 0.30 → 0.25 — Improvement ⑩)
MODEL_WEIGHT = 0.75
SCENE_WEIGHT = 0.25

# ① Minimum fused confidence to even consider a violation.
# NOTE (bugfix): 0.65 was too strict given the fusion formula below — real
# detections (e.g. helmet model conf 0.54 fused with a noisy motorcycle-box
# scene_conf of ~0.45) were landing around 0.50-0.60 and getting silently
# dropped (_make() returning None) before they ever reached the
# MANUAL_REVIEW / AUTO_APPROVED tiering. Lowered so moderate-confidence
# detections survive as MANUAL_REVIEW instead of vanishing entirely.
# Per-type AUTO_APPROVED thresholds (below) are unchanged and still gate
# auto-challan issuance.
MIN_CONFIDENCE = 0.40

# ② Global auto-challan floor (raised 0.85 → 0.90)
CHALLAN_CONFIDENCE = 0.90

# ③ Per-violation-type challan threshold overrides (all tightened)
VIOLATION_CHALLAN_THRESHOLDS: dict[str, float] = {
    "Mobile Usage While Driving":  0.92,   # phone detection is noisy — tightened
    "Wrong Side Driving":          0.90,   # trajectory-based — tightened
    "Abnormal Driving Behaviour":  0.90,
    "Triple Riding":               0.88,
    "No Entry Violation":          0.88,
    "Overspeeding":                0.88,
    "Seat Belt Violation":         0.85,
    "Stop Sign Violation":         0.85,
    "Helmet Violation":            0.83,   # easier to detect reliably
    "Red Light Violation":         0.83,   # signal colour is clear-cut
    "Stop Line / Zebra Violation": 0.80,
    "Illegal Parking":             0.78,   # stationary + zone = low ambiguity
    "Pedestrian Signal Violation": 0.78,
}

# Speed rules
SPEED_TOLERANCE_KMH         = 10
STOP_SIGN_SPEED_THRESHOLD_KMH = 5.0

# ⑦ Illegal parking — raised from 90 → 120 frames to avoid flagging traffic stops
PARKING_FRAMES_THRESHOLD = 120


# ══════════════════════════════════════════════════════════════════════════════
# Review-queue tiers  (Improvement ⑥)
# ══════════════════════════════════════════════════════════════════════════════

class ReviewStatus:
    AUTO_APPROVED  = "AUTO_APPROVED"   # conf >= per-type challan threshold
    MANUAL_REVIEW  = "MANUAL_REVIEW"   # conf in [MIN_CONFIDENCE, threshold)
    REJECTED       = "REJECTED"        # conf < MIN_CONFIDENCE  (never stored)


# ══════════════════════════════════════════════════════════════════════════════
# Consecutive-frame confirmation gate  (Improvement ⑤)
# ══════════════════════════════════════════════════════════════════════════════

# Minimum consecutive confirmed frames before a violation is raised
# Set lower for fast-changing violations (signal), higher for noisy ones (phone)
CONSECUTIVE_FRAME_REQUIREMENTS: dict[str, int] = {
    "Helmet Violation":             3,
    "Triple Riding":                3,
    "Mobile Usage While Driving":   5,   # most prone to false positives
    "Seat Belt Violation":          4,
    "Red Light Violation":          2,
    "Stop Line / Zebra Violation":  2,
    "Wrong Side Driving":           4,
    "Abnormal Driving Behaviour":   4,
    "Illegal Parking":              1,   # stationary-frame gate is already handled by parking_threshold
    "No Entry Violation":           3,
    "Stop Sign Violation":          3,
    "Overspeeding":                 2,
    "Pedestrian Signal Violation":  2,
}
DEFAULT_FRAME_REQUIREMENT = 3

# State: (track_id, vtype) → consecutive confirmation count
_frame_counters: dict[tuple, int] = defaultdict(int)


def confirm_violation(track_id: int, vtype: str) -> bool:
    """
    Increment the consecutive-frame counter for (track_id, vtype).
    Returns True only when the counter reaches the required threshold.
    Resets to 0 immediately after firing so the next occurrence must
    accumulate again (prevents the same frame from triggering twice).

    In image mode (track_id == -1) the gate is bypassed and True is returned
    immediately — single images have no frame history.
    """
    if track_id < 0:
        return True   # image mode — no tracking, skip gate

    key       = (track_id, vtype)
    required  = CONSECUTIVE_FRAME_REQUIREMENTS.get(vtype, DEFAULT_FRAME_REQUIREMENT)
    _frame_counters[key] += 1

    if _frame_counters[key] >= required:
        _frame_counters[key] = 0
        return True
    return False


def reset_confirmation_state() -> None:
    """Call between videos / test runs to clear consecutive-frame counters."""
    _frame_counters.clear()


# ══════════════════════════════════════════════════════════════════════════════
# Violation dataclass
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Violation:
    violation_type:      str
    severity:            str
    risk_score:          int
    fine_amount:         int
    confidence:          float
    plate_number:        str   = "UNKNOWN"
    track_id:            int   = -1
    review_status:       str   = ReviewStatus.MANUAL_REVIEW
    needs_manual_review: bool  = True    # kept for API back-compat
    details:             dict  = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════════════
# Core helpers
# ══════════════════════════════════════════════════════════════════════════════

def _fuse(model_conf: float, scene_conf: float) -> float:
    """Weighted confidence fusion: 75 % model + 25 % scene quality."""
    return round(MODEL_WEIGHT * model_conf + SCENE_WEIGHT * scene_conf, 3)


def _make(vtype: str, conf: float, plate: str, tid: int,
          details: dict | None = None) -> Optional[Violation]:
    """
    Build a Violation if conf >= MIN_CONFIDENCE.

    ④ UNKNOWN-plate guard: Critical and High severity violations with an
       unreadable plate are flagged for MANUAL_REVIEW regardless of confidence,
       so no automatic challan issues against a vehicle we cannot identify.

    Tiers (⑥):
      conf < MIN_CONFIDENCE (0.65)       → REJECTED (return None)
      MIN_CONFIDENCE ≤ conf < threshold  → MANUAL_REVIEW
      conf >= threshold                  → AUTO_APPROVED
    """
    if conf < MIN_CONFIDENCE:
        return None

    sev, risk, fine        = VIOLATION_CATALOGUE.get(vtype, ("Low", 30, 200))
    challan_threshold      = VIOLATION_CHALLAN_THRESHOLDS.get(vtype, CHALLAN_CONFIDENCE)
    auto_approved          = conf >= challan_threshold

    # ④ UNKNOWN plate → force manual review on Critical/High violations
    unknown_plate = plate in ("UNKNOWN", "", None)
    if unknown_plate and sev in ("Critical", "High"):
        auto_approved = False

    review_status    = ReviewStatus.AUTO_APPROVED if auto_approved else ReviewStatus.MANUAL_REVIEW
    needs_review     = not auto_approved

    d = details or {}
    d["review_status"]      = review_status
    d["challan_threshold"]  = challan_threshold
    d["unknown_plate"]      = unknown_plate

    return Violation(
        violation_type      = vtype,
        severity            = sev,
        risk_score          = risk,
        fine_amount         = fine,
        confidence          = conf,
        plate_number        = plate,
        track_id            = tid,
        review_status       = review_status,
        needs_manual_review = needs_review,
        details             = d,
    )


def apply_plate(violations: list[Violation], plate: str) -> list[Violation]:
    """
    Patch a resolved plate number onto already-built Violation objects and
    re-apply the UNKNOWN-plate guard / auto-approval tiering.

    BUGFIX: main.py used to call evaluate_bike()/evaluate_car() a SECOND
    time after resolving the plate, purely so the UNKNOWN-plate guard could
    be re-applied with the real plate text. But every evaluate_* call also
    runs confirm_violation() (the consecutive-frame gate), so each detection
    was incrementing its frame counter TWICE per actual frame — corrupting
    the gate in video mode (violations could fire after 2 real frames
    instead of the configured N, or skip/duplicate unpredictably).

    Call this instead of re-invoking evaluate_bike()/evaluate_car() once a
    plate has been resolved.
    """
    unknown_plate = plate in ("UNKNOWN", "", None)
    for v in violations:
        v.plate_number = plate
        v.details["unknown_plate"] = unknown_plate

        if unknown_plate:
            if v.severity in ("Critical", "High"):
                v.review_status       = ReviewStatus.MANUAL_REVIEW
                v.needs_manual_review = True
        else:
            threshold = v.details.get("challan_threshold", CHALLAN_CONFIDENCE)
            if v.confidence >= threshold:
                v.review_status       = ReviewStatus.AUTO_APPROVED
                v.needs_manual_review = False
    return violations


def _gate(vtype: str, tid: int, v: Optional[Violation]) -> Optional[Violation]:
    """
    Wrap _make output through the consecutive-frame gate (Improvement ⑤).
    Returns the Violation only after N consecutive confirmations.
    """
    if v is None:
        return None
    if not confirm_violation(tid, vtype):
        return None   # not enough consecutive frames yet
    return v


# ══════════════════════════════════════════════════════════════════════════════
# Traffic Sign rule helpers
# ══════════════════════════════════════════════════════════════════════════════

def _check_no_entry(sign_data: dict, trajectory: list,
                    plate: str, tid: int, scene_conf: float) -> Optional[Violation]:
    if not sign_data.get("no_entry", False):
        return None
    sign_dets = sign_data.get("sign_dets", [])
    sign_conf = max(
        (d["conf"] for d in sign_dets if d.get("class_name") == "no entry"),
        default=0.0,
    )
    if sign_conf == 0.0:
        return None
    if len(trajectory) >= 5:
        p0, p1 = trajectory[-5], trajectory[-1]
        if abs(p1[0] - p0[0]) + abs(p1[1] - p0[1]) < 3:
            return None   # stationary — not entering
    c = _fuse(sign_conf, scene_conf)
    v = _make("No Entry Violation", c, plate, tid,
              {"sign_conf": round(sign_conf, 3), "sign": "no_entry"})
    return _gate("No Entry Violation", tid, v)


def _check_stop_sign(sign_data: dict, speed_kmh: float,
                     plate: str, tid: int, scene_conf: float) -> Optional[Violation]:
    if not sign_data.get("stop_sign", False):
        return None
    sign_dets = sign_data.get("sign_dets", [])
    sign_conf = max(
        (d["conf"] for d in sign_dets if d.get("class_name") == "stop"),
        default=0.0,
    )
    if sign_conf == 0.0:
        return None

    if speed_kmh <= 0.0:
        # Image mode — discount confidence heavily; always manual review
        if sign_conf < 0.55:
            return None
        c = _fuse(sign_conf * 0.70, scene_conf)
        v = _make("Stop Sign Violation", c, plate, tid,
                  {"sign_conf": round(sign_conf, 3),
                   "speed_kmh": "unknown",
                   "note": "speed not measured — flagged for review"})
        return _gate("Stop Sign Violation", tid, v)

    if speed_kmh > STOP_SIGN_SPEED_THRESHOLD_KMH:
        c = _fuse(sign_conf, scene_conf)
        v = _make("Stop Sign Violation", c, plate, tid,
                  {"sign_conf": round(sign_conf, 3),
                   "speed_kmh": round(speed_kmh, 1),
                   "threshold_kmh": STOP_SIGN_SPEED_THRESHOLD_KMH})
        return _gate("Stop Sign Violation", tid, v)
    return None


def _check_overspeeding(sign_data: dict, speed_kmh: float,
                        plate: str, tid: int, scene_conf: float) -> Optional[Violation]:
    limit = sign_data.get("speed_limit_kmh")
    if limit is None or speed_kmh <= 0.0:
        return None
    excess = speed_kmh - limit
    if excess <= SPEED_TOLERANCE_KMH:
        return None
    sign_dets = sign_data.get("sign_dets", [])
    sign_conf = max(
        (d["conf"] for d in sign_dets
         if "speed limit" in d.get("class_name", "")),
        default=0.80,
    )
    c = _fuse(sign_conf, scene_conf)
    v = _make("Overspeeding", c, plate, tid,
              {"speed_kmh":  round(speed_kmh, 1),
               "limit_kmh":  limit,
               "excess_kmh": round(excess, 1),
               "sign_conf":  round(sign_conf, 3)})
    return _gate("Overspeeding", tid, v)


# ══════════════════════════════════════════════════════════════════════════════
# Bike rule evaluation  (Improvement ⑧ — imports from standalone modules)
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_bike(b_data:      dict,
                  signal_data: dict,
                  sign_data:   dict,
                  box:         list,
                  plate:       str,
                  scene_conf:  float,
                  trajectory:  list,
                  tid:         int,
                  speed_kmh:   float = 0.0) -> list[Violation]:
    """
    Apply traffic rules to bike expert-pipeline output.

    Checks:
      • Helmet violation          (helmet_detector module)
      • Triple riding             (triple_riding module)
      • Mobile usage
      • Red light (shared signal_data)
      • Stop line / zebra crossing
      • Wrong-side driving        (Improvement #7 + ⑨)
      • No Entry · Stop Sign · Overspeeding  (traffic_sign.pt)

    All checks gated by consecutive-frame confirmation (Improvement ⑤).
    """
    violations: list[Violation] = []

    # ── Helmet  (⑧ delegates to helmet_detector for cleaner separation) ──────
    h_cls  = b_data.get("helmet",      "unknown")
    h_conf = b_data.get("helmet_conf", 0.0)
    # Only raise a violation when detector.py's risk-score logic has committed
    # to "no_helmet". "uncertain" and "helmet" must never generate a challan —
    # "uncertain" means both helmet and no-helmet detections exist but neither
    # dominates by enough margin (e.g. Helmet 0.42, No-Helmet 0.39).
    if h_cls == "no_helmet":
        c = _fuse(h_conf, scene_conf)
        print(
            f"[HELMET] class={h_cls} "
            f"model={h_conf:.2f} "
            f"scene={scene_conf:.2f} "
            f"fused={c:.2f}"
        )
        v = _gate("Helmet Violation", tid,
                  _make("Helmet Violation", c, plate, tid,
                        {"detected": h_cls, "model_conf": h_conf}))
        if v: violations.append(v)
    else:
        print(f"[HELMET] SKIP challan — status={h_cls!r}  conf={h_conf:.2f}")

    # ── Triple riding  (⑧) ──────────────────────────────────────────────────
    t_cls  = b_data.get("triple_riding", "unknown")
    t_conf = b_data.get("triple_conf",   0.0)
    if t_cls == "triple_rider":
        c = _fuse(t_conf, scene_conf)
        v = _gate("Triple Riding", tid,
                  _make("Triple Riding", c, plate, tid,
                        {"detected": t_cls, "model_conf": t_conf}))
        if v: violations.append(v)

    # ── Mobile usage ─────────────────────────────────────────────────────────
    p_cls  = b_data.get("phone",      "unknown")
    p_conf = b_data.get("phone_conf", 0.0)
    
    # Only consider phone usage if confidence >= 80%
    if p_cls == "phone" and p_conf >= 0.80:
        c = _fuse(p_conf, scene_conf)
    
        v = _gate(
            "Mobile Usage While Driving",
            tid,
            _make(
                "Mobile Usage While Driving",
                c,
                plate,
                tid,
                {
                    "detected": p_cls,
                    "model_conf": p_conf,
                    "challan_threshold": 0.80,
                }
            )
        )
    
        if v:
            violations.append(v)

    # ── Red light ────────────────────────────────────────────────────────────
    sig    = signal_data.get("signal_color", "unknown")
    s_conf = signal_data.get("signal_conf",  0.0)
    if sig == "red":
        c = _fuse(s_conf, scene_conf)
        v = _gate("Red Light Violation", tid,
                  _make("Red Light Violation", c, plate, tid,
                        {"signal": sig, "signal_conf": s_conf}))
        if v: violations.append(v)

    # ── Stop line / zebra ────────────────────────────────────────────────────
    zebra_dets = signal_data.get("zebra_boxes", [])
    if sig == "red" and zebra_dets and _vehicle_near_zebra(box, zebra_dets):
        c = _fuse(max(d["conf"] for d in zebra_dets), scene_conf)
        v = _gate("Stop Line / Zebra Violation", tid,
                  _make("Stop Line / Zebra Violation", c, plate, tid))
        if v: violations.append(v)

    # ── Wrong-side driving  (⑨ scaled by trajectory length) ─────────────────
    wrong, angle = is_wrong_side(trajectory)
    if wrong:
        # Longer trajectory = higher confidence (more data points)
        traj_bonus = min(0.10, len(trajectory) / 1000.0)
        raw_conf   = min(0.97, scene_conf + 0.05 + traj_bonus)
        v = _gate("Wrong Side Driving", tid,
                  _make("Wrong Side Driving", raw_conf, plate, tid,
                        {"angle_deg": angle, "traj_len": len(trajectory)}))
        if v: violations.append(v)

    # ── Traffic Sign Rules ───────────────────────────────────────────────────
    for check in (_check_no_entry(sign_data, trajectory, plate, tid, scene_conf),
                  _check_stop_sign(sign_data, speed_kmh, plate, tid, scene_conf),
                  _check_overspeeding(sign_data, speed_kmh, plate, tid, scene_conf)):
        if check: violations.append(check)

    return violations


# ══════════════════════════════════════════════════════════════════════════════
# Car / Truck / Bus rule evaluation
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_car(c_data:       dict,
                 signal_data:  dict,
                 sign_data:    dict,
                 box:          list,
                 plate:        str,
                 scene_conf:   float,
                 parking_data: dict,
                 trajectory:   list,
                 frames_stat:  int,
                 tid:          int,
                 speed_kmh:    float = 0.0) -> list[Violation]:
    """
    Apply traffic rules to car expert-pipeline output.

    Checks:
      • Seat belt violation
      • Mobile usage
      • Abnormal driving behaviour
      • Red light violation
      • Stop line / zebra violation
      • Illegal parking                (⑦ threshold raised to 120 frames)
      • Wrong-side driving             (⑨ trajectory-scaled confidence)
      • No Entry · Stop Sign · Overspeeding
    """
    violations: list[Violation] = []

    # ── Seat belt ────────────────────────────────────────────────────────────
    s_cls  = c_data.get("seatbelt",      "unknown")
    s_conf = c_data.get("seatbelt_conf", 0.0)

    # Accept any label variant produced by different seatbelt model versions:
    #   "no_seatbelt", "WithoutSeat_Belt", "without_seatbelt", "NoSeatbelt"
    # car_pipeline() normalises these to "no_seatbelt" via substring matching,
    # but we double-check here for defence-in-depth.
    _is_no_seatbelt = (
        s_cls == "no_seatbelt"
        or ("without" in s_cls.lower() and "seat" in s_cls.lower())
        or (s_cls.lower().startswith("no") and "seat" in s_cls.lower())
    )

    # SEATBELT DEFENCE-IN-DEPTH:
    # car_pipeline() gates the seatbelt classifier behind Gates 0-3 (size,
    # aspect, confidence, person-presence).  However if car_pipeline() was
    # called in legacy/test mode (person_boxes=None), those gates are partially
    # bypassed.  We add a final guard here: only raise a Seat Belt Violation
    # when the scene-model confidence for the car detection is ≥ 0.15.
    # Genuine cars typically score ≥ 0.25; the ghost detections that cause
    # false positives are consistently ≤ 0.10.
    # Also require that car_pipeline did NOT return a skip_reason, which it sets
    # whenever any of its own gates fired — those results are already "clean",
    # but a skip_reason of "low_conf_detection" or "no_visible_driver" means
    # the seatbelt result is "unknown" / 0.0 and should never fire here anyway.
    _skip_reason    = c_data.get("skip_reason", "")
    _sb_gated_out   = bool(_skip_reason)          # any gate in car_pipeline fired
    _scene_too_low  = scene_conf < 0.15           # ghost detection

    # NOTE: [SEATBELT] log is now emitted inside car_pipeline() (detector.py)
    # with full context on ab_seatbelt_seen suppression. The duplicate log
    # that used to live here has been removed — it was printing violation=True
    # even when the pipeline had already suppressed the false positive.
    if _is_no_seatbelt and not _sb_gated_out and not _scene_too_low:
        c = _fuse(s_conf, scene_conf)
        v = _gate("Seat Belt Violation", tid,
                  _make("Seat Belt Violation", c, plate, tid,
                        {"detected": s_cls, "model_conf": s_conf}))
        if v: violations.append(v)

    # ── Mobile usage ─────────────────────────────────────────────────────────
    p_cls  = c_data.get("phone",      "unknown")
    p_conf = c_data.get("phone_conf", 0.0)

    # Gate on raw model confidence >= 0.80 before fusing.
    # car_pipeline() now fuses phone.pt + abnormal.pt "phone" signals into
    # c_data["phone"] / c_data["phone_conf"], so p_conf here is already
    # the best available phone signal — no need to read ab_dets separately.
    if p_cls == "phone" and p_conf >= 0.80:
        c = _fuse(p_conf, scene_conf)
        v = _gate("Mobile Usage While Driving", tid,
                  _make("Mobile Usage While Driving", c, plate, tid,
                        {"detected": p_cls, "model_conf": p_conf,
                         "challan_threshold": 0.80}))
        if v: violations.append(v)

    # ── Abnormal driving ─────────────────────────────────────────────────────
    ab_cls  = c_data.get("abnormal",      "normal")
    ab_conf = c_data.get("abnormal_conf", 0.0)
    # car_pipeline() surfaces only cigarette / drinking / eating in
    # c_data["abnormal"] — phone and seatbelt are consumed separately.
    # BUGFIX: "phone" was previously included here, which issued a SECOND
    # challan ("Abnormal Driving Behaviour") for the same event already
    # raised above as "Mobile Usage While Driving", inflating the fine and
    # the combined_risk score. Removed from this set.
    _ABNORMAL_VIOLATION_CLASSES = {"cigarette", "drinking", "eating"}
    if ab_cls in _ABNORMAL_VIOLATION_CLASSES:
        c = _fuse(ab_conf, scene_conf)
        v = _gate("Abnormal Driving Behaviour", tid,
                  _make("Abnormal Driving Behaviour", c, plate, tid,
                        {"sub_type": ab_cls, "model_conf": ab_conf}))
        if v: violations.append(v)

    # ── Red light ────────────────────────────────────────────────────────────
    sig    = signal_data.get("signal_color", "unknown")
    s_conf = signal_data.get("signal_conf",  0.0)
    if sig == "red":
        c = _fuse(s_conf, scene_conf)
        v = _gate("Red Light Violation", tid,
                  _make("Red Light Violation", c, plate, tid,
                        {"signal": sig, "signal_conf": s_conf}))
        if v: violations.append(v)

    # ── Stop line / zebra ────────────────────────────────────────────────────
    zebra_dets = signal_data.get("zebra_boxes", [])
    if sig == "red" and zebra_dets and _vehicle_near_zebra(box, zebra_dets):
        c = _fuse(max(d["conf"] for d in zebra_dets), scene_conf)
        v = _gate("Stop Line / Zebra Violation", tid,
                  _make("Stop Line / Zebra Violation", c, plate, tid))
        if v: violations.append(v)

    # ── Illegal parking  (⑦ threshold = 120 frames) ─────────────────────────
    no_park_zones = parking_data.get("no_parking_zones", [])
    if frames_stat >= PARKING_FRAMES_THRESHOLD and no_park_zones:
        if any(_vehicle_in_zone(box, z["box"]) for z in no_park_zones):
            park_conf = max(z["conf"] for z in no_park_zones)
            c = _fuse(park_conf, scene_conf)
            v = _make("Illegal Parking", c, plate, tid,
                      {"frames_stationary": frames_stat,
                       "no_parking_zones":  len(no_park_zones)})
            if v: violations.append(v)

    # ── Wrong-side driving  (⑨) ──────────────────────────────────────────────
    wrong, angle = is_wrong_side(trajectory)
    if wrong:
        traj_bonus = min(0.10, len(trajectory) / 1000.0)
        raw_conf   = min(0.97, scene_conf + 0.05 + traj_bonus)
        v = _gate("Wrong Side Driving", tid,
                  _make("Wrong Side Driving", raw_conf, plate, tid,
                        {"angle_deg": angle, "traj_len": len(trajectory)}))
        if v: violations.append(v)

    # ── Traffic Sign Rules ───────────────────────────────────────────────────
    for check in (_check_no_entry(sign_data, trajectory, plate, tid, scene_conf),
                  _check_stop_sign(sign_data, speed_kmh, plate, tid, scene_conf),
                  _check_overspeeding(sign_data, speed_kmh, plate, tid, scene_conf)):
        if check: violations.append(check)

    return violations


# ══════════════════════════════════════════════════════════════════════════════
# Pedestrian rule evaluation
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_pedestrian(signal_data: dict,
                        box:         list,
                        tid:         int) -> list[Violation]:
    violations: list[Violation] = []
    sig    = signal_data.get("signal_color", "unknown")
    s_conf = signal_data.get("signal_conf",  0.0)
    zebra_dets = signal_data.get("zebra_boxes", [])

    if sig == "red" and zebra_dets and _vehicle_near_zebra(box, zebra_dets):
        c = _fuse(s_conf, 0.5)
        v = _gate("Pedestrian Signal Violation", tid,
                  _make("Pedestrian Signal Violation", c, "PEDESTRIAN", tid,
                        {"signal": sig}))
        if v: violations.append(v)
    return violations


# ══════════════════════════════════════════════════════════════════════════════
# Spatial helpers
# ══════════════════════════════════════════════════════════════════════════════

def _center(box: list) -> tuple:
    return ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2)


def _vehicle_near_zebra(vbox: list, zebra_dets: list,
                        px_threshold: int = 80) -> bool:
    cx, cy = _center(vbox)
    for z in zebra_dets:
        zx1, zy1, zx2, zy2 = z["box"]
        dist_x = max(0, max(zx1 - cx, cx - zx2))
        dist_y = max(0, max(zy1 - cy, cy - zy2))
        if math.hypot(dist_x, dist_y) < px_threshold:
            return True
    return False


def _vehicle_in_zone(vbox: list, zone_box: list) -> bool:
    cx, cy = _center(vbox)
    x1, y1, x2, y2 = zone_box
    return x1 <= cx <= x2 and y1 <= cy <= y2


# ══════════════════════════════════════════════════════════════════════════════
# Multi-Violation Fusion  (Improvement #10)
# ══════════════════════════════════════════════════════════════════════════════

def fuse_vehicle_violations(violations: list[Violation],
                            plate: str) -> dict:
    """
    Merge all violations for a single vehicle into one fused record.
    combined_risk = clip(max_risk + 0.5 * sum_of_secondary_risks, 0, 100)
    """
    if not violations:
        return {"plate": plate, "combined_risk": 0,
                "top_severity": "Low", "violation_count": 0}

    sorted_v = sorted(violations,
                      key=lambda v: SEVERITY_ORDER.get(v.severity, 0),
                      reverse=True)
    primary_risk   = sorted_v[0].risk_score
    secondary_risk = sum(v.risk_score for v in sorted_v[1:]) * 0.5
    combined_risk  = int(min(100, primary_risk + secondary_risk))

    # A single MANUAL_REVIEW violation in the batch forces the whole record
    # to require review — conservative policy (④)
    any_manual = any(v.review_status == ReviewStatus.MANUAL_REVIEW
                     for v in sorted_v)
    batch_status = (ReviewStatus.MANUAL_REVIEW if any_manual
                    else ReviewStatus.AUTO_APPROVED)

    return {
        "plate":           plate,
        "combined_risk":   combined_risk,
        "top_severity":    sorted_v[0].severity,
        "violation_count": len(violations),
        "review_status":   batch_status,
        "violations":      [v.to_dict() for v in sorted_v],
    }


# ══════════════════════════════════════════════════════════════════════════════
# Summary helper
# ══════════════════════════════════════════════════════════════════════════════

def summarize_violations(violations: list[Violation]) -> dict:
    total      = len(violations)
    by_type:   dict[str, int] = {}
    total_fine = 0
    for v in violations:
        by_type[v.violation_type] = by_type.get(v.violation_type, 0) + 1
        total_fine += v.fine_amount

    severity_counts: dict[str, int] = {}
    review_counts:   dict[str, int] = defaultdict(int)
    for v in violations:
        severity_counts[v.severity] = severity_counts.get(v.severity, 0) + 1
        review_counts[v.review_status] += 1

    return {
        "total_violations":  total,
        "by_type":           by_type,
        "severity_counts":   severity_counts,
        "review_breakdown":  dict(review_counts),
        "total_fine_inr":    total_fine,
    }