"""
fraud_guard.py
──────────────────────────────────────────────────────────────
Feature 4 — Challan Fraud / OCR Error Detection

Problems solved:
  1. Low-confidence OCR  →  manual review flag instead of auto-challan
  2. Known OCR confusion pairs  →  similarity check before issuing
  3. Duplicate challans  →  same plate + same violation within time window
  4. Impossible plates   →  format validation as a final gate
  5. Blacklist check     →  flagged/stolen plates trigger alert, not challan

Usage:
    from fraud_guard import FraudGuard
    guard = FraudGuard()
    result = guard.check(plate, violations, ocr_conf)
    if result.approved:
        issue_challan(...)
    else:
        queue_for_review(result)
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Configuration ─────────────────────────────────────────────────────────────

OCR_CONF_THRESHOLD    = 0.70    # below this → manual review
DUPLICATE_WINDOW_SEC  = 300     # 5 minutes — same plate + violation = duplicate
BLACKLIST_PATH        = Path("data/blacklist_plates.json")

# Indian plate regex (loose — XX 00 XX 0000)
_PLATE_RE = re.compile(r"^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{1,4}$")

# Common OCR confusion pairs on number plates
_OCR_CONFUSIONS: list[tuple[str, str]] = [
    ("O", "0"), ("I", "1"), ("S", "5"),
    ("Z", "2"), ("B", "8"), ("G", "6"),
    ("D", "0"), ("Q", "0"), ("U", "0"),
]


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class GuardResult:
    approved:       bool
    plate:          str
    ocr_confidence: float
    flags:          list[str]  = field(default_factory=list)
    action:         str        = "issue_challan"  # or "manual_review" / "suppress"
    reason:         str        = ""

    def to_dict(self) -> dict:
        return {
            "approved":       self.approved,
            "plate":          self.plate,
            "ocr_confidence": round(self.ocr_confidence, 3),
            "flags":          self.flags,
            "action":         self.action,
            "reason":         self.reason,
        }


# ── Main guard class ──────────────────────────────────────────────────────────

class FraudGuard:
    """
    Single entry-point for all challan quality / fraud checks.

    Methods:
        check(plate, violations, ocr_conf, camera_id)
            → GuardResult

        load_blacklist() / add_to_blacklist(plate, reason)
    """

    def __init__(self):
        # In-memory deduplication log: (plate, vtype) → last_seen_epoch
        self._seen: dict[tuple, float] = {}
        self._blacklist: dict[str, str] = {}
        self._load_blacklist()

    # ── Main check ────────────────────────────────────────────────────────────

    def check(self,
              plate:      str,
              violations: list,  # list of Violation objects or dicts
              ocr_conf:   float,
              camera_id:  str = "CAM-01") -> GuardResult:
        """
        Run all fraud / quality checks.

        Returns GuardResult with approved=True only when all pass.
        """
        flags:  list[str] = []
        action: str       = "issue_challan"

        plate_clean = plate.upper().replace(" ", "")

        # 1. Format validation
        if plate_clean not in ("UNKNOWN", "PEDESTRIAN", "") \
                and not _PLATE_RE.match(plate_clean):
            flags.append(f"INVALID_FORMAT:{plate_clean}")
            action = "manual_review"

        # 2. OCR confidence gate
        if ocr_conf < OCR_CONF_THRESHOLD:
            flags.append(f"LOW_OCR_CONF:{ocr_conf:.2f}")
            action = "manual_review"

        # 3. Possible OCR confusion — check similarity to already-issued plates
        confusion = self._check_confusion(plate_clean)
        if confusion:
            flags.append(f"OCR_CONFUSION_RISK:{confusion}")
            if action == "issue_challan":
                action = "manual_review"

        # 4. Blacklist check
        if plate_clean in self._blacklist:
            reason = self._blacklist[plate_clean]
            flags.append(f"BLACKLISTED:{reason}")
            action = "alert"   # highest priority — don't just flag, alert

        # 5. Duplicate detection
        vtypes = _extract_vtypes(violations)
        dups   = self._check_duplicates(plate_clean, vtypes)
        if dups:
            flags.append(f"DUPLICATE:{','.join(dups)}")
            action = "suppress"   # don't re-issue within window

        # 6. Unknown plate
        if plate_clean in ("UNKNOWN", ""):
            flags.append("PLATE_NOT_READ")
            action = "manual_review"

        approved = action == "issue_challan"
        reason   = "; ".join(flags) if flags else "all checks passed"

        # Record this plate+violation for future dup detection
        if approved:
            self._record_seen(plate_clean, vtypes)

        return GuardResult(
            approved       = approved,
            plate          = plate,
            ocr_confidence = ocr_conf,
            flags          = flags,
            action         = action,
            reason         = reason,
        )

    # ── Duplicate detection ───────────────────────────────────────────────────

    def _check_duplicates(self, plate: str, vtypes: list[str]) -> list[str]:
        now  = time.time()
        dups = []
        for vt in vtypes:
            key  = (plate, vt)
            last = self._seen.get(key, 0)
            if now - last < DUPLICATE_WINDOW_SEC:
                dups.append(vt)
        return dups

    def _record_seen(self, plate: str, vtypes: list[str]) -> None:
        now = time.time()
        for vt in vtypes:
            self._seen[(plate, vt)] = now

    # ── OCR confusion check ───────────────────────────────────────────────────

    def _check_confusion(self, plate: str) -> str:
        """
        Generate common OCR variants of this plate and see if any were
        recently issued.  Returns a suspicious variant if found, else "".
        """
        variants = _generate_ocr_variants(plate)
        now      = time.time()
        for var in variants:
            for key, last in self._seen.items():
                if key[0] == var and now - last < DUPLICATE_WINDOW_SEC * 2:
                    return var
        return ""

    # ── Blacklist ─────────────────────────────────────────────────────────────

    def _load_blacklist(self) -> None:
        if BLACKLIST_PATH.exists():
            try:
                self._blacklist = json.loads(BLACKLIST_PATH.read_text())
                print(f"[FraudGuard] Blacklist loaded: {len(self._blacklist)} plates")
            except Exception as e:
                print(f"[FraudGuard] Blacklist load error: {e}")

    def add_to_blacklist(self, plate: str, reason: str = "flagged") -> None:
        self._blacklist[plate.upper().replace(" ", "")] = reason
        BLACKLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        BLACKLIST_PATH.write_text(json.dumps(self._blacklist, indent=2))
        print(f"[FraudGuard] Added to blacklist: {plate} ({reason})")

    def load_blacklist(self) -> dict:
        return dict(self._blacklist)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_vtypes(violations: list) -> list[str]:
    out = []
    for v in violations:
        if isinstance(v, dict):
            out.append(v.get("violation_type", ""))
        else:
            out.append(getattr(v, "violation_type", ""))
    return [x for x in out if x]


def _generate_ocr_variants(plate: str) -> list[str]:
    """
    Generate likely OCR mis-reads of a plate string.
    Only single-character substitutions are checked (most common OCR errors).
    """
    variants = set()
    confusion_map = {a: b for a, b in _OCR_CONFUSIONS}
    confusion_map.update({b: a for a, b in _OCR_CONFUSIONS})

    for i, ch in enumerate(plate):
        if ch in confusion_map:
            variants.add(plate[:i] + confusion_map[ch] + plate[i + 1:])

    variants.discard(plate)
    return list(variants)


# ── Module-level singleton ─────────────────────────────────────────────────────

_guard: Optional[FraudGuard] = None


def get_guard() -> FraudGuard:
    global _guard
    if _guard is None:
        _guard = FraudGuard()
    return _guard