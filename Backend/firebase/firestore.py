"""
firebase/firestore_service.py
──────────────────────────────────────────────────────────────
Write violation records and challans to Firestore.

Collections
  violations  — one doc per individual violation (sub-records of a challan)
  challans    — one doc per challan (the fused, per-vehicle record)
"""

from datetime import datetime
from firebase.firebase_config import db


# ── Violations ─────────────────────────────────────────────────────────────────

def save_violation(challan: dict, image_urls: dict) -> None:
    """
    Write one Firestore document per violation inside a challan.
    Document ID: <challan_id>-<index>  (e.g. CHN-A30EEB80-0)
    """
    challan_id = challan.get("challan_id", "UNKNOWN")
    for i, v in enumerate(challan.get("violations", [])):
        doc_id = f"{challan_id}-{i}"
        doc = {
            "id":             doc_id,
            "challan_id":     challan_id,
            "plate":          challan.get("plate_number", "UNKNOWN"),
            "camera":         challan.get("camera_id",   "CAM-01"),
            "location":       challan.get("location",    "Unknown"),
            "violation_type": v.get("violation_type",    "Unknown"),
            "severity":       v.get("severity",          "Medium"),
            "confidence":     v.get("confidence",        0.0),
            "risk_score":     v.get("risk_score",        0),
            "fine_amount":    v.get("fine_amount",       0),
            "review_status":  v.get("review_status",     "MANUAL_REVIEW"),
            "timestamp":      challan.get("issued_at",
                                         datetime.now().isoformat()),
            "image_url":      image_urls.get("full_url",    ""),
            "vehicle_url":    image_urls.get("vehicle_url", ""),
            "plate_url":      image_urls.get("plate_url",   ""),
        }
        try:
            db.collection("violations").document(doc_id).set(doc)
        except Exception as e:
            print(f"[Firebase/Firestore] violations write failed ({doc_id}): {e}")


# ── Challans ───────────────────────────────────────────────────────────────────

def save_challan(challan: dict, image_urls: dict) -> None:
    """
    Write one Firestore document for the whole challan (fused record).
    Document ID: challan_id  (e.g. CHN-A30EEB80)
    """
    challan_id = challan.get("challan_id", "UNKNOWN")
    doc = {
        "challan_id":    challan_id,
        "plate":         challan.get("plate_number",  "UNKNOWN"),
        "camera":        challan.get("camera_id",     "CAM-01"),
        "location":      challan.get("location",      "Unknown"),
        "total_fine":    challan.get("total_fine_inr", 0),
        "combined_risk": challan.get("combined_risk",  50),
        "top_severity":  challan.get("top_severity",   "Medium"),
        "review_status": challan.get("review_status",  "MANUAL_REVIEW"),
        "auto_challan":  challan.get("auto_challan",   False),
        "issued_at":     challan.get("issued_at",
                                     datetime.now().isoformat()),
        "image_url":     image_urls.get("full_url",    ""),
        "vehicle_url":   image_urls.get("vehicle_url", ""),
        "plate_url":     image_urls.get("plate_url",   ""),
        "violations":    challan.get("violations",     []),
    }
    try:
        db.collection("challans").document(challan_id).set(doc)
    except Exception as e:
        print(f"[Firebase/Firestore] challans write failed ({challan_id}): {e}")


# ── Combined helper (called from main.py) ──────────────────────────────────────

def push_to_firestore(challan: dict, image_urls: dict) -> None:
    """Single call that writes both collections atomically."""
    save_violation(challan, image_urls)
    save_challan(challan, image_urls)