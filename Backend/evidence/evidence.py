"""
evidence.py
──────────────────────────────────────────────────────────────
Evidence Generator — Level 4 / Layer 5 of HMATES architecture.

Improvement #8 — Evidence Image Cropping
  Saves full_image.jpg + vehicle_crop.jpg + plate_crop.jpg per incident.

evidence/
  ├── images/
  │     ├── RID_full.jpg
  │     ├── RID_vehicle.jpg    ← NEW (#8)
  │     └── RID_plate.jpg      ← NEW (#8)
  ├── metadata/
  │     └── RID_meta.json
  └── challans/
        └── CHN-RID.json
"""

import json
import uuid
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path

# ── Directory setup ────────────────────────────────────────────────────────────

EVIDENCE_DIR = Path("evidence")
IMAGE_DIR    = EVIDENCE_DIR / "images"
META_DIR     = EVIDENCE_DIR / "metadata"
CHALLAN_DIR  = EVIDENCE_DIR / "challans"

for _d in [IMAGE_DIR, META_DIR, CHALLAN_DIR]:
    _d.mkdir(parents=True, exist_ok=True)


# ── Visual constants ───────────────────────────────────────────────────────────

VIOLATION_COLORS: dict[str, tuple] = {
    "Helmet Violation":             (0,   0,   255),
    "Triple Riding":                (0,   140, 255),
    "Seat Belt Violation":          (0,   0,   200),
    "Mobile Usage While Driving":   (255, 0,   255),
    "Red Light Violation":          (0,   0,   180),
    "Stop Line / Zebra Violation":  (30,  144, 255),
    "Illegal Parking":              (128, 0,   128),
    "Wrong Side Driving":           (0,   69,  255),
    "Pedestrian Signal Violation":  (255, 165, 0),
    "Abnormal Driving Behaviour":   (0,   215, 255),
    "DEFAULT":                      (0,   255, 255),
}

SEVERITY_COLORS: dict[str, tuple] = {
    "Critical": (0,   0,   255),
    "High":     (0,   100, 255),
    "Medium":   (0,   215, 255),
    "Low":      (0,   255, 0),
}

FONT  = cv2.FONT_HERSHEY_SIMPLEX
THICK = 2


def _draw_box(img: np.ndarray, box: list, label: str,
              conf: float = None, color: tuple = (0, 255, 0)) -> np.ndarray:
    x1, y1, x2, y2 = box
    text = f"{label} {conf:.2f}" if conf is not None else label
    cv2.rectangle(img, (x1, y1), (x2, y2), color, THICK)
    (tw, th), _ = cv2.getTextSize(text, FONT, 0.55, THICK)
    ly = max(y1 - 4, th + 4)
    cv2.rectangle(img, (x1, ly - th - 4), (x1 + tw + 4, ly + 2), color, -1)
    cv2.putText(img, text, (x1 + 2, ly), FONT, 0.55, (255, 255, 255), THICK)
    return img


# ── Annotation ─────────────────────────────────────────────────────────────────

def annotate_image(img: np.ndarray, scene: dict,
                   violations: list, signal_data: dict) -> np.ndarray:
    """
    Draw all detections, signal state, zebra boxes, and violation banners
    on a copy of the frame. Returns the annotated image.
    """
    out = img.copy()

    # All scene detections (green)
    for det in scene.get("all", []):
        _draw_box(out, det["box"], det["class_name"], det["conf"], (0, 200, 0))

    # Traffic light indicator
    sig = signal_data.get("signal_color", "unknown")
    ind = {"red": (0, 0, 255), "green": (0, 255, 0),
           "yellow": (0, 255, 255), "off": (100, 100, 100)}.get(sig, (100, 100, 100))
    cv2.circle(out, (40, 40), 18, ind, -1)
    cv2.putText(out, f"Signal: {sig.upper()}", (65, 48), FONT, 0.65, ind, 2)

    # Zebra crossings (orange)
    for zd in signal_data.get("zebra_boxes", []):
        _draw_box(out, zd["box"], "Zebra", zd["conf"], (255, 165, 0))

    # Violation banners — one line each with severity, type, plate, fine, risk
    h, _ = out.shape[:2]
    for i, v in enumerate(violations):
        color    = VIOLATION_COLORS.get(v.violation_type, VIOLATION_COLORS["DEFAULT"])
        sev_col  = SEVERITY_COLORS.get(v.severity, (0, 255, 255))
        banner   = (f"[{v.severity}] {v.violation_type}"
                    f"  |  {v.plate_number}"
                    f"  |  Rs.{v.fine_amount}"
                    f"  |  Risk:{v.risk_score}"
                    f"  |  Conf:{v.confidence:.0%}")
        cv2.putText(out, banner, (10, 28 + i * 26), FONT, 0.46, color, 2)

    # Timestamp watermark
    w = out.shape[1]
    cv2.putText(out, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                (w - 215, h - 10), FONT, 0.44, (200, 200, 200), 1)
    return out


# ── Improvement #8: Evidence crop helpers ──────────────────────────────────────

def crop_vehicle(img: np.ndarray, box: list, pad: int = 12) -> np.ndarray:
    """Return a padded crop of the vehicle region."""
    h, w = img.shape[:2]
    x1, y1, x2, y2 = box
    return img[max(0, y1 - pad):min(h, y2 + pad),
               max(0, x1 - pad):min(w, x2 + pad)]


def crop_plate(img: np.ndarray, box: list, pad: int = 5) -> np.ndarray:
    """Return a padded crop of the plate region."""
    h, w = img.shape[:2]
    x1, y1, x2, y2 = box
    return img[max(0, y1 - pad):min(h, y2 + pad),
               max(0, x1 - pad):min(w, x2 + pad)]


def _save_crop(img: np.ndarray, path: Path) -> bool:
    """Write crop to disk; return True on success."""
    if img is None or img.size == 0:
        return False
    return cv2.imwrite(str(path), img)


def save_evidence_crops(img: np.ndarray, rid: str, ts: str,
                        vehicle_box: list = None,
                        plate_box:   list = None) -> dict:
    """
    Improvement #8 — save vehicle_crop.jpg and plate_crop.jpg.

    Returns dict of {key: path_str} for keys that were saved.
    """
    saved = {}

    if vehicle_box:
        vc   = crop_vehicle(img, vehicle_box)
        vpath = IMAGE_DIR / f"{rid}_{ts}_vehicle.jpg"
        if _save_crop(vc, vpath):
            saved["vehicle_crop"] = str(vpath)

    if plate_box:
        pc   = crop_plate(img, plate_box)
        ppath = IMAGE_DIR / f"{rid}_{ts}_plate.jpg"
        if _save_crop(pc, ppath):
            saved["plate_crop"] = str(ppath)

    return saved


# ── Evidence record ────────────────────────────────────────────────────────────

def create_evidence_record(plate: str, violations: list,
                           image_path:        str = "",
                           vehicle_crop_path: str = "",
                           plate_crop_path:   str = "",
                           location:  str = "Unknown",
                           camera_id: str = "CAM-01",
                           track_id:  int = None,
                           fused_record: dict = None) -> dict:
    rid = str(uuid.uuid4())[:8].upper()
    return {
        "record_id":      rid,
        "timestamp":      datetime.now().isoformat(),
        "camera_id":      camera_id,
        "location":       location,
        "track_id":       track_id,
        "plate_number":   plate,
        "image_path":     image_path,
        "vehicle_crop":   vehicle_crop_path,   # Improvement #8
        "plate_crop":     plate_crop_path,     # Improvement #8
        "violations":     [v.to_dict() for v in violations],
        "total_fine":     sum(v.fine_amount for v in violations),
        "combined_risk":  fused_record.get("combined_risk", 50) if fused_record else 50,
        "top_severity":   fused_record.get("top_severity", "Medium") if fused_record else "Medium",
        "status":         "pending_review",
    }


def save_evidence_images(img: np.ndarray, record: dict,
                         annotated:   np.ndarray = None,
                         vehicle_box: list = None,
                         plate_box:   list = None) -> str:
    """
    Persist annotated full image + vehicle/plate crops to disk and stamp
    their local paths onto `record`.

    Does NOT write the metadata JSON — call write_evidence_metadata(record)
    afterwards, once you've merged in anything else that should be saved
    alongside (e.g. Firebase Storage URLs from upload_evidence_pack()).
    This split exists because previously save_evidence() wrote the JSON
    immediately, before the Firebase upload step ran, so the Storage URLs
    never made it into the saved metadata (BUGFIX, see main.py).

    Returns record_id.
    """
    rid = record["record_id"]
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    record["_ts"] = ts  # remembered so write_evidence_metadata() names the file consistently

    full_path = IMAGE_DIR / f"{rid}_{ts}_full.jpg"
    cv2.imwrite(str(full_path), annotated if annotated is not None else img)
    record["image_path"] = str(full_path)

    crops = save_evidence_crops(img, rid, ts, vehicle_box, plate_box)
    record.update(crops)

    v_ok = "✓" if "vehicle_crop" in crops else "–"
    p_ok = "✓" if "plate_crop"   in crops else "–"
    print(f"[Evidence] {rid}  full:✓  vehicle:{v_ok}  plate:{p_ok}  → {full_path.name}")
    return rid


def write_evidence_metadata(record: dict) -> Path:
    """
    Write (or overwrite) the JSON metadata file for a record.
    Call AFTER save_evidence_images() and after merging in any extra
    fields (e.g. Firebase Storage URLs) so they get persisted too.
    """
    rid = record["record_id"]
    ts  = record.pop("_ts", None) or datetime.now().strftime("%Y%m%d_%H%M%S")
    meta_path = META_DIR / f"{rid}_{ts}.json"
    with open(meta_path, "w") as f:
        json.dump(record, f, indent=2)
    return meta_path


def save_evidence(img: np.ndarray, record: dict,
                  annotated:   np.ndarray = None,
                  vehicle_box: list = None,
                  plate_box:   list = None) -> str:
    """
    Convenience wrapper: save images + write metadata in one call.
    Use this for callers that have no extra fields (e.g. Firebase URLs)
    to merge in between the two steps — e.g. the video-frame pipeline.
    For the Firebase-enabled image pipeline, call save_evidence_images()
    and write_evidence_metadata() separately instead (see main.py).

    Returns the record_id string.
    """
    rid = save_evidence_images(img, record, annotated, vehicle_box, plate_box)
    write_evidence_metadata(record)
    return rid


# ── Challan generation ─────────────────────────────────────────────────────────

def generate_challan(record: dict, persist: bool = True) -> dict:
    """
    Build a challan dict from a record; optionally persist it.

    persist: when True (default), write the challan JSON to
    evidence/challans/ and print the formatted console notice. Pass False
    when the caller doesn't want this challan written/counted yet — e.g.
    main.py's video pipeline calls process_frame(..., save=False, ...) for
    every sampled frame and applies its own 5-second dedup window
    afterwards to decide what actually gets persisted. Previously this
    function ignored the caller's save intent entirely and wrote a new
    CHN-<uuid>.json to disk on every single call, flooding
    evidence/challans/ with duplicates during video processing regardless
    of any dedup logic layered on top (BUGFIX, see main.py).
    """
    challan_id = "CHN-" + record["record_id"]
    challan = {
        "challan_id":     challan_id,
        "issued_at":      datetime.now().isoformat(),
        "plate_number":   record["plate_number"],
        "location":       record["location"],
        "camera_id":      record["camera_id"],
        "violations":     record["violations"],
        "total_fine_inr": record["total_fine"],
        "combined_risk":  record.get("combined_risk", 50),
        "top_severity":   record.get("top_severity", "Medium"),
        "evidence_image": record.get("image_path", ""),
        "vehicle_crop":   record.get("vehicle_crop", ""),   # Improvement #8
        "plate_crop":     record.get("plate_crop",   ""),   # Improvement #8
        # BUGFIX: these were being uploaded to Firebase Storage and sent to
        # Firestore, but never copied onto `record` before this function ran,
        # so they never appeared here or in GET /challans. See main.py.
        "full_url":       record.get("full_url",    ""),
        "vehicle_url":    record.get("vehicle_url",  ""),
        "plate_url":      record.get("plate_url",    ""),
        "payment_due":    "30 days from issue date",
        "status":         "issued",
    }

    if not persist:
        return challan

    cp = CHALLAN_DIR / f"{challan_id}.json"
    with open(cp, "w") as f:
        json.dump(challan, f, indent=2)

    # Formatted console notice
    sev   = record.get("top_severity", "?")
    risk  = record.get("combined_risk", 0)
    print("\n" + "═" * 62)
    print(f"  CHALLAN  {challan_id}  |  {sev} risk ({risk}/100)")
    print("═" * 62)
    print(f"  Plate    : {record['plate_number']}")
    print(f"  Location : {record['location']}  |  Camera: {record['camera_id']}")
    print("─" * 62)
    for v in record["violations"]:
        print(f"  [{v['severity']:<8}] {v['violation_type']:<36}"
              f"Rs.{v['fine_amount']:>6,}  "
              f"Risk:{v['risk_score']:>3}  "
              f"Conf:{v['confidence']:.0%}")
    print("─" * 62)
    print(f"  TOTAL FINE    : Rs. {record['total_fine']:,}")
    print(f"  COMBINED RISK : {risk}/100  [{sev}]")
    print("═" * 62 + "\n")
    return challan


# ── Load records ───────────────────────────────────────────────────────────────

def load_all_records() -> list:
    """Load and return all saved metadata JSON files as a list of dicts."""
    records = []
    for f in META_DIR.glob("*.json"):
        try:
            with open(f) as fh:
                records.append(json.load(fh))
        except Exception as e:
            print(f"[WARN] Could not load {f}: {e}")
    return records