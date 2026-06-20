"""
explainer.py
──────────────────────────────────────────────────────────────
Feature 7 — Generative AI Violation Explanation

Uses the Anthropic Claude API to generate a concise, court-ready
natural-language explanation for each challan.

Output example:
  "Vehicle RJ14AB1234 was detected crossing the stop line at a red
   traffic signal on MG Road, Jaipur at 14:32 on 19-Jun-2025. The
   rider was also not wearing a helmet. Combined risk score: 82/100
   (High). Confidence: 91%. Total fine: Rs. 6,000."

This adds explainability — a key requirement for AI systems used in
legal / governmental contexts.

Usage:
    from explainer import explain_challan
    text = explain_challan(challan_record)

Requires:
    pip install anthropic
    ANTHROPIC_API_KEY set in environment (or passed directly)
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional


# ── Template fallback (no API key) ────────────────────────────────────────────

def _template_explanation(record: dict) -> str:
    """
    Deterministic rule-based explanation.
    Used when the Anthropic API is unavailable.
    """
    plate     = record.get("plate_number", "UNKNOWN")
    location  = record.get("location",    "Unknown location")
    camera    = record.get("camera_id",   "?")
    fine      = record.get("total_fine",  0)
    risk      = record.get("combined_risk", "?")
    severity  = record.get("top_severity",  "?")
    ts_raw    = record.get("timestamp",   "")

    try:
        ts = datetime.fromisoformat(ts_raw).strftime("%d-%b-%Y at %H:%M")
    except Exception:
        ts = ts_raw[:16] if ts_raw else "unknown time"

    violations = record.get("violations", [])
    vlines = []
    for v in violations:
        vtype = v.get("violation_type", "Unknown violation")
        conf  = v.get("confidence", 0)
        sev   = v.get("severity",   "?")
        vlines.append(
            f"  • [{sev}] {vtype} (confidence: {conf:.0%})"
        )
    vblock = "\n".join(vlines) if vlines else "  • No violations recorded"

    return (
        f"Vehicle {plate} was detected committing traffic violations "
        f"at {location} (Camera: {camera}) on {ts}.\n\n"
        f"Violations detected:\n{vblock}\n\n"
        f"Combined risk score: {risk}/100 [{severity}]. "
        f"Total fine: Rs. {fine:,}."
    )


# ── AI explanation ─────────────────────────────────────────────────────────────

def _ai_explanation(record: dict, api_key: str) -> Optional[str]:
    """
    Call Claude claude-sonnet-4-6 to generate a concise explanation.
    Returns None on any error (caller will fall back to template).
    """
    try:
        import anthropic
    except ImportError:
        return None

    plate     = record.get("plate_number", "UNKNOWN")
    location  = record.get("location",    "Unknown")
    camera    = record.get("camera_id",   "?")
    fine      = record.get("total_fine",  0)
    risk      = record.get("combined_risk", "?")
    severity  = record.get("top_severity",  "?")
    ts_raw    = record.get("timestamp",   "")

    try:
        ts = datetime.fromisoformat(ts_raw).strftime("%d-%b-%Y at %H:%M")
    except Exception:
        ts = ts_raw[:16] if ts_raw else "unknown time"

    violations = record.get("violations", [])
    vlist = "\n".join(
        f"- {v.get('violation_type','?')} "
        f"(severity: {v.get('severity','?')}, "
        f"confidence: {v.get('confidence',0):.0%}, "
        f"fine: Rs.{v.get('fine_amount',0):,})"
        for v in violations
    )

    prompt = f"""You are a traffic enforcement AI system generating a court-ready explanation.

Incident data:
  Plate:      {plate}
  Location:   {location}
  Camera:     {camera}
  Time:       {ts}
  Risk score: {risk}/100 [{severity}]
  Total fine: Rs. {fine:,}

Violations:
{vlist}

Write ONE clear paragraph (3-5 sentences) explaining what happened in plain English.
Include: what the vehicle did wrong, when and where, confidence level, and the fine.
Do not use bullet points. Do not add headings. Be factual and concise."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp   = client.messages.create(
            model      = "claude-sonnet-4-6",
            max_tokens = 300,
            messages   = [{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        print(f"[Explainer] API error: {e}")
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def explain_challan(record: dict,
                    api_key: str = None,
                    use_ai:  bool = True) -> str:
    """
    Generate a human-readable explanation for a challan record.

    Args:
        record:  challan or evidence record dict
        api_key: Anthropic API key (reads ANTHROPIC_API_KEY env var if None)
        use_ai:  set False to always use the template (faster, no API call)

    Returns:
        Plain-text explanation string.
    """
    if use_ai:
        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if key:
            ai_text = _ai_explanation(record, key)
            if ai_text:
                return ai_text
        else:
            if use_ai:
                print("[Explainer] ANTHROPIC_API_KEY not set — using template.")

    return _template_explanation(record)


def explain_batch(records: list[dict],
                  api_key: str = None,
                  use_ai:  bool = True) -> list[dict]:
    """
    Add an 'explanation' field to each record in a list.
    Returns the same list (mutated in-place).
    """
    for r in records:
        r["explanation"] = explain_challan(r, api_key, use_ai)
    return records