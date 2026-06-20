"""
analytics.py
──────────────────────────────────────────────────────────────
Analytics and Reporting.
Generates violation statistics, trends, and searchable records
from the evidence metadata saved by evidence.py.
"""

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def _load():
    from evidence.evidence import load_all_records
    return load_all_records()


# ── Core statistics ────────────────────────────────────────────────────────────

def violation_counts(records: list = None) -> Counter:
    """Count occurrences of each violation type. Returns Counter."""
    if records is None:
        records = _load()
    c = Counter()
    for r in records:
        for v in r.get("violations", []):
            c[v["violation_type"]] += 1
    return c


def total_fines_collected(records: list = None) -> int:
    if records is None:
        records = _load()
    return sum(r.get("total_fine", 0) for r in records)


def fines_by_violation(records: list = None) -> dict:
    """Total fine value grouped by violation type."""
    if records is None:
        records = _load()
    t = defaultdict(int)
    for r in records:
        for v in r.get("violations", []):
            t[v["violation_type"]] += v.get("fine_amount", 0)
    return dict(t)


def violations_by_hour(records: list = None) -> dict:
    """Distribution of violations across hours 0–23."""
    if records is None:
        records = _load()
    h = defaultdict(int)
    for r in records:
        try:
            hour = datetime.fromisoformat(r["timestamp"]).hour
            h[hour] += len(r.get("violations", []))
        except Exception:
            pass
    return dict(sorted(h.items()))


def violations_by_camera(records: list = None) -> dict:
    """Violations per camera, sorted descending — useful for hotspot detection."""
    if records is None:
        records = _load()
    c = defaultdict(int)
    for r in records:
        c[r.get("camera_id", "UNKNOWN")] += len(r.get("violations", []))
    return dict(sorted(c.items(), key=lambda x: -x[1]))


def repeat_offenders(records: list = None, min_count: int = 2) -> dict:
    """Plates with >= min_count incident records. Returns {plate: count}."""
    if records is None:
        records = _load()
    c = Counter()
    for r in records:
        p = r.get("plate_number", "UNKNOWN")
        if p not in ("UNKNOWN", "PEDESTRIAN", ""):
            c[p] += 1
    return {p: n for p, n in c.items() if n >= min_count}


def daily_trend(records: list = None, days: int = 7) -> dict:
    """Violation counts per calendar day for the last N days."""
    if records is None:
        records = _load()
    d = defaultdict(int)
    cutoff = datetime.now() - timedelta(days=days)
    for r in records:
        try:
            dt = datetime.fromisoformat(r["timestamp"])
            if dt >= cutoff:
                d[dt.strftime("%Y-%m-%d")] += len(r.get("violations", []))
        except Exception:
            pass
    return dict(sorted(d.items()))


# ── Summary report ─────────────────────────────────────────────────────────────

def generate_summary_report(records: list = None) -> dict:
    """Build and return a comprehensive summary dict."""
    if records is None:
        records = _load()

    counts = violation_counts(records)
    cam    = violations_by_camera(records)

    return {
        "generated_at":         datetime.now().isoformat(),
        "total_records":        len(records),
        "total_violations":     sum(counts.values()),
        "total_fines_inr":      total_fines_collected(records),
        "violations_by_type":   dict(counts.most_common()),
        "fines_by_type_inr":    fines_by_violation(records),
        "violations_by_hour":   violations_by_hour(records),
        "violations_by_camera": cam,
        "repeat_offenders":     repeat_offenders(records),
        "daily_trend_7d":       daily_trend(records, 7),
        "top_violation":        counts.most_common(1)[0][0] if counts else "None",
        "top_camera_hotspot":   list(cam.keys())[0] if cam else "None",
    }


def print_report(report: dict = None) -> None:
    """Pretty-print the summary report to stdout."""
    if report is None:
        report = generate_summary_report()
    print("\n" + "═" * 62)
    print("  HMATES ANALYTICS REPORT")
    print(f"  {report['generated_at'][:19]}")
    print("═" * 62)
    print(f"  Records    : {report['total_records']}")
    print(f"  Violations : {report['total_violations']}")
    print(f"  Fines INR  : Rs. {report['total_fines_inr']:,}")
    print(f"  Top        : {report['top_violation']}")
    print(f"  Hotspot    : {report['top_camera_hotspot']}")
    print("─" * 62)
    print("  By Violation Type:")
    for vt, cnt in report["violations_by_type"].items():
        fine = report["fines_by_type_inr"].get(vt, 0)
        bar  = "█" * min(cnt, 30)
        print(f"    {vt:<38} {cnt:>4}  Rs.{fine:>8,}  {bar}")
    print("─" * 62)
    print("  Repeat Offenders (top 10):")
    for plate, cnt in sorted(report["repeat_offenders"].items(),
                              key=lambda x: -x[1])[:10]:
        print(f"    {plate}  →  {cnt} incidents")
    print("═" * 62 + "\n")


def save_report(output_path: str = "evidence/report.json",
                records: list = None) -> dict:
    report = generate_summary_report(records)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[Analytics] Report saved → {output_path}")
    return report


# ── Searchable record lookup ───────────────────────────────────────────────────

def search_by_plate(plate: str, records: list = None) -> list:
    if records is None:
        records = _load()
    return [r for r in records if r.get("plate_number", "").upper() == plate.upper()]


def search_by_date(date_str: str, records: list = None) -> list:
    """date_str format: YYYY-MM-DD"""
    if records is None:
        records = _load()
    return [r for r in records if r.get("timestamp", "").startswith(date_str)]


def search_by_violation(vtype: str, records: list = None) -> list:
    if records is None:
        records = _load()
    return [r for r in records
            if any(v["violation_type"] == vtype for v in r.get("violations", []))]


def search_by_camera(camera_id: str, records: list = None) -> list:
    if records is None:
        records = _load()
    return [r for r in records if r.get("camera_id") == camera_id]