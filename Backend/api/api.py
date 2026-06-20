"""
api.py
──────────────────────────────────────────────────────────────
HMATES FastAPI REST Layer  (v1.1)

Makes the system deployable as a microservice behind any front-end,
mobile app, or third-party traffic management platform.

Endpoints:
  POST /upload                          Process a single image
  POST /upload/video                    Process a video clip (async, returns job_id)
  GET  /status/{job_id}                 Poll async video job
  GET  /report                          Full analytics report from saved evidence
  GET  /evidence                        List evidence records with real image URLs
  GET  /evidence/{id}                   Single evidence record with image URLs
  GET  /evidence-images/{file}          Static evidence JPEGs (full/vehicle/plate crops)
  GET  /search/plate/{plate}            Records for a number plate
  GET  /search/date/{date}              Records for a calendar date (YYYY-MM-DD)
  GET  /search/camera/{cam_id}          Records by camera ID
  GET  /search/violation/{vtype}        Records by violation type
  GET  /challans                        List all issued challans (paginated)
  POST /challans/{record_id}/review     Update review status of a challan
  PUT  /challans/{record_id}/violations Officer violation corrections + fine override
  GET  /health                          Liveness check

Run:
  pip install fastapi uvicorn python-multipart
  uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import logging
import os
import json
import uuid
import asyncio
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator, model_validator

# ── HMATES imports ────────────────────────────────────────────────────────────
from detectors.preprocess import load_image
from main import process_frame, process_video
from analytics.analytics import (
    generate_summary_report,
    search_by_plate,
    search_by_date,
    search_by_violation,
    search_by_camera,
)
from evidence.evidence import CHALLAN_DIR, META_DIR, IMAGE_DIR

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("hmates.api")

# ── Constants ─────────────────────────────────────────────────────────────────
MAX_IMAGE_BYTES = 20 * 1024 * 1024   # 20 MB
MAX_VIDEO_BYTES = 500 * 1024 * 1024  # 500 MB

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/avi", "video/quicktime", "video/x-matroska"}

VALID_ACTIONS = {"approved", "rejected", "escalated"}

# Fine schedule — single source of truth in the API layer.
# Mirrors rule_engine.py so the officer-correction endpoint can validate fines.
FINE_SCHEDULE: dict[str, int] = {
    "Helmet Violation":             500,
    "Triple Riding":               1000,
    "Seat Belt Violation":          500,
    "Mobile Usage While Driving":  5000,
    "Red Light Violation":         1000,
    "Stop Line / Zebra Violation":  500,
    "Illegal Parking":              500,
    "Wrong Side Driving":          5000,
    "Pedestrian Signal Violation":  500,
    "Abnormal Driving Behaviour":  2000,
}

# Internal status vocabulary → four states the React frontend styles.
_STATUS_MAP = {
    "pending_review": "pending",
    "issued":         "pending",
    "AUTO_APPROVED":  "approved",
    "REJECTED":       "rejected",
    "MANUAL_REVIEW":  "escalated",
}

# ── Executor & async job store ────────────────────────────────────────────────
_executor = ThreadPoolExecutor(max_workers=4)
_jobs: dict[str, dict] = {}   # replace with Redis for multi-worker deployments


# ── Lifespan (replaces deprecated on_event) ───────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    log.info("HMATES API starting up — evidence image dir: %s", IMAGE_DIR)
    yield
    log.info("HMATES API shutting down.")
    _executor.shutdown(wait=False)


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="HMATES API",
    description="Hierarchical Multi-Agent Traffic Enforcement & Automated Challan System",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve saved evidence images via GET /evidence-images/<filename>
app.mount(
    "/evidence-images",
    StaticFiles(directory=str(IMAGE_DIR)),
    name="evidence-images",
)


# ── Pydantic models ───────────────────────────────────────────────────────────

class ReviewRequest(BaseModel):
    action: str          # "approved" | "rejected" | "escalated"
    notes: str = ""

    @field_validator("action")
    @classmethod
    def action_must_be_valid(cls, v: str) -> str:
        if v not in VALID_ACTIONS:
            raise ValueError(f"action must be one of {sorted(VALID_ACTIONS)}")
        return v


class ViolationItem(BaseModel):
    """Single violation entry as produced by the rule engine."""
    violation_type: str
    fine_amount: int
    severity: str = "Medium"
    confidence: float = 1.0

    @field_validator("violation_type")
    @classmethod
    def type_must_be_known(cls, v: str) -> str:
        if v not in FINE_SCHEDULE:
            raise ValueError(
                f"Unknown violation_type '{v}'. Valid types: {sorted(FINE_SCHEDULE)}"
            )
        return v

    @field_validator("fine_amount")
    @classmethod
    def fine_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("fine_amount must be ≥ 0")
        return v

    @field_validator("confidence")
    @classmethod
    def conf_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class OfficerCorrection(BaseModel):
    """
    Officer-reviewed violation list with recalculated fine.
    Stores both the AI detections (for retraining) and the approved set.
    """
    officer_violations: list[ViolationItem]
    officer_total_fine: int
    officer_remark: str = ""
    ai_violations: list[dict] = []   # raw AI output; not validated to stay flexible

    @model_validator(mode="after")
    def fine_must_match_violations(self) -> "OfficerCorrection":
        computed = sum(v.fine_amount for v in self.officer_violations)
        if self.officer_total_fine != computed:
            raise ValueError(
                f"officer_total_fine ({self.officer_total_fine}) does not match "
                f"sum of violation fines ({computed}). Recalculate before submitting."
            )
        return self


# ── Helpers ───────────────────────────────────────────────────────────────────

def _assert_file_size(data: bytes, max_bytes: int, label: str) -> None:
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"{label} exceeds maximum size of {max_bytes // (1024 * 1024)} MB.",
        )


def _assert_content_type(content_type: str | None, allowed: set[str], label: str) -> None:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct not in allowed:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported {label} type '{ct}'. Allowed: {sorted(allowed)}",
        )


def _decode_image(file_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Could not decode image — file may be corrupt.")
    return img


def _find_challan_file(record_id: str) -> Path | None:
    """Locate the saved challan JSON whose record_id or challan_id matches."""
    # Fast path: the file is named after its challan_id (CHN-<rid>.json)
    candidate = CHALLAN_DIR / f"CHN-{record_id}.json"
    if candidate.exists():
        return candidate
    # Slow path: scan directory (handles edge-cases where ID scheme differs)
    for f in CHALLAN_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        if data.get("record_id") == record_id or data.get("challan_id") == record_id:
            return f
    return None


def _image_url(path_str: str | None) -> str | None:
    """Convert a filesystem path to a frontend-reachable /evidence-images/ URL."""
    if not path_str:
        return None
    return f"/evidence-images/{Path(path_str).name}"


def _hydrate_record_urls(data: dict) -> dict:
    """Attach *_url fields to a record without removing the original local paths."""
    data["image_url"]        = _image_url(data.get("image_path") or data.get("evidence_image"))
    data["vehicle_crop_url"] = _image_url(data.get("vehicle_crop"))
    data["plate_crop_url"]   = _image_url(data.get("plate_crop"))
    return data


def _normalize_status(data: dict) -> str:
    raw = data.get("review_status") or data.get("status") or "pending"
    return _STATUS_MAP.get(raw, raw.lower() if isinstance(raw, str) else "pending")


def _top_violation(violations: list) -> tuple[Optional[str], Optional[float]]:
    """Return the highest-confidence violation type + confidence from a list."""
    if not violations:
        return None, None
    top = max(violations, key=lambda v: v.get("confidence", 0) or 0)
    return top.get("violation_type"), top.get("confidence")


def _to_frontend_shape(data: dict) -> dict:
    """
    Flatten a metadata/challan record into the flat field names consumed by
    the React frontend (EvidenceLocker, AlertPanel, Dashboard, ReviewQueue,
    Violations) while preserving every original field so existing consumers
    don't break.

    Adds: id, plate, violation, type, confidence, camera, timestamp,
          fine, status, image_name, image_url, vehicle_crop_url, plate_crop_url.
    Also exposes officer_violations / officer_total_fine when present so
    the Evidence Locker can show AI vs officer-approved side by side.
    """
    data = _hydrate_record_urls(data)

    # Prefer officer-approved violations for display; fall back to AI output.
    violations = data.get("officer_violations") or data.get("violations", [])
    vtype, conf = _top_violation(violations)
    image_path  = data.get("image_path") or data.get("evidence_image")

    data["id"]         = data.get("record_id") or data.get("challan_id", "")
    data["plate"]      = data.get("plate_number", "UNKNOWN")
    data["violation"]  = vtype or data.get("top_severity")
    data["type"]       = vtype
    data["confidence"] = round(conf * 100) if conf is not None else None
    data["camera"]     = data.get("camera_id")
    data["timestamp"]  = data.get("timestamp") or data.get("issued_at")
    data["fine"]       = data.get("officer_total_fine") or data.get("total_fine") or data.get("total_fine_inr")
    data["status"]     = _normalize_status(data)
    # Filename only; EvidenceCard builds the full URL as
    # `${API_BASE}/evidence-images/${image_name}`
    data["image_name"] = Path(image_path).name if image_path else None
    return data


def _read_json_dir(directory: Path, limit: int) -> list[dict]:
    """Return up to `limit` parsed JSON files from `directory`, newest first."""
    files = sorted(directory.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:limit]
    records: list[dict] = []
    for f in files:
        try:
            records.append(json.loads(f.read_text()))
        except Exception as exc:
            log.warning("Skipping malformed JSON %s: %s", f.name, exc)
    return records


# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs for details."},
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Meta"])
def health():
    """Liveness check — returns server time and worker count."""
    return {
        "status":    "ok",
        "timestamp": datetime.now().isoformat(),
        "workers":   _executor._max_workers,
    }


@app.post("/upload", summary="Process a single image", tags=["Ingestion"])
async def upload_image(
    file:     UploadFile = File(...),
    camera:   str  = Query("CAM-01",  description="Camera identifier"),
    location: str  = Query("Unknown", description="Physical location label"),
    save:     bool = Query(True,       description="Persist evidence to disk"),
):
    """
    Upload a JPG/PNG/WebP traffic image.
    Returns detected violations, generated challans, and a frame summary.
    Max size: 20 MB.
    """
    _assert_content_type(file.content_type, ALLOWED_IMAGE_TYPES, "image")
    raw_bytes = await file.read()
    _assert_file_size(raw_bytes, MAX_IMAGE_BYTES, "Image")

    img = _decode_image(raw_bytes)
    log.info(
        "Image upload — camera=%s location=%s size=%dx%d  "
        "dtype=%s  min=%d  max=%d",
        camera, location,
        img.shape[1], img.shape[0],
        img.dtype, int(img.min()), int(img.max()),
    )
    # Uncomment to save the exact array reaching inference for comparison with
    # standalone tests.  Keep commented in production.
    cv2.imwrite("debug_api_input.jpg", img)
    print("[DEBUG] Saved debug_api_input.jpg")

    loop   = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        _executor,
        lambda: process_frame(img, camera_id=camera, location=location, save=save),
    )

    first_challan = (result.get("challans") or [{}])[0]
    raw_img = first_challan.get("evidence_image") or first_challan.get("image_path") or ""

    return {
        "status":          "ok",
        "camera":          camera,
        "location":        location,
        "annotated_image": _image_url(raw_img) if raw_img else None,
        "summary":         result.get("summary"),
        "violations":      result.get("violations", []),
        "challans":        [_to_frontend_shape(c) for c in (result.get("challans") or [])],
        # Convenience fields for UploadAnalysis card display
        "plate": first_challan.get("plate_number", ""),
        "ocr": {
            "plateText":  first_challan.get("plate_number", ""),
            "confidence": (result.get("summary") or {}).get("ocr_confidence"),
        },
        "vehicles": [
            {
                "type":       v.get("class_name", "vehicle"),
                "confidence": int((v.get("conf") or 0) * 100),
            }
            for v in (result.get("summary", {}).get("detected_objects") or [])
        ],
    }


@app.post("/upload/video", summary="Submit a video clip for async processing", tags=["Ingestion"])
async def upload_video(
    file:     UploadFile = File(...),
    camera:   str  = Query("CAM-01"),
    location: str  = Query("Unknown"),
    save:     bool = Query(True),
):
    """
    Upload a video file. Returns a job_id immediately.
    Poll GET /status/{job_id} for results. Max size: 500 MB.
    """
    _assert_content_type(file.content_type, ALLOWED_VIDEO_TYPES, "video")
    raw_bytes = await file.read()
    _assert_file_size(raw_bytes, MAX_VIDEO_BYTES, "Video")

    job_id = str(uuid.uuid4())[:8].upper()
    suffix = Path(file.filename or "clip.mp4").suffix or ".mp4"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(raw_bytes)
    tmp.close()

    _jobs[job_id] = {"status": "processing", "started_at": datetime.now().isoformat()}
    log.info("Video job %s queued — camera=%s location=%s", job_id, camera, location)

    def _run() -> None:
        try:
            result = process_video(tmp.name, camera_id=camera, location=location, save=save)
            _jobs[job_id].update({
                "status":      "done",
                "result":      result,
                "finished_at": datetime.now().isoformat(),
            })
            log.info("Video job %s completed.", job_id)
        except Exception as exc:
            log.exception("Video job %s failed.", job_id)
            _jobs[job_id].update({"status": "error", "error": str(exc)})
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    asyncio.get_running_loop().run_in_executor(_executor, _run)
    return {"job_id": job_id, "status": "processing"}


@app.get("/status/{job_id}", summary="Poll async video job", tags=["Ingestion"])
def job_status(job_id: str):
    """Returns current status of a video processing job."""
    if job_id not in _jobs:
        raise HTTPException(404, detail=f"Job '{job_id}' not found.")
    return _jobs[job_id]


@app.get("/report", summary="Full analytics report", tags=["Analytics"])
def analytics_report():
    """Return the complete analytics summary generated from all saved evidence."""
    return generate_summary_report()


@app.get("/search/plate/{plate}", summary="Records for a number plate", tags=["Search"])
def by_plate(plate: str):
    hits = search_by_plate(plate.upper().strip())
    return {"plate": plate.upper(), "count": len(hits), "records": hits}


@app.get("/search/date/{date}", summary="Records for a date (YYYY-MM-DD)", tags=["Search"])
def by_date(date: str):
    # Basic format guard — full ISO validation left to the analytics layer.
    if len(date) != 10 or date[4] != "-" or date[7] != "-":
        raise HTTPException(400, detail="date must be in YYYY-MM-DD format.")
    hits = search_by_date(date)
    return {"date": date, "count": len(hits), "records": hits}


@app.get("/search/camera/{cam_id}", summary="Records by camera ID", tags=["Search"])
def by_camera(cam_id: str):
    hits = search_by_camera(cam_id)
    return {"camera_id": cam_id, "count": len(hits), "records": hits}


@app.get("/search/violation/{vtype}", summary="Records by violation type", tags=["Search"])
def by_violation(vtype: str):
    hits = search_by_violation(vtype)
    return {"violation_type": vtype, "count": len(hits), "records": hits}


@app.get("/evidence", summary="List evidence records with real image URLs", tags=["Evidence"])
def list_evidence(
    limit:  int = Query(100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(0,   ge=0,           description="Skip this many records (pagination)"),
):
    """
    Returns saved evidence metadata (one per incident) with image_url /
    vehicle_crop_url / plate_crop_url fields for the Evidence Locker screen.
    """
    all_files = sorted(META_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    page      = all_files[offset: offset + limit]
    records   = []
    for f in page:
        try:
            records.append(_to_frontend_shape(json.loads(f.read_text())))
        except Exception as exc:
            log.warning("Skipping malformed evidence JSON %s: %s", f.name, exc)
    return {"total": len(all_files), "offset": offset, "count": len(records), "records": records}


@app.get("/evidence/{record_id}", summary="Single evidence record with image URLs", tags=["Evidence"])
def get_evidence(record_id: str):
    """Returns one evidence record by its record_id."""
    for f in META_DIR.glob(f"{record_id}_*.json"):
        try:
            return _to_frontend_shape(json.loads(f.read_text()))
        except Exception:
            continue
    raise HTTPException(404, detail=f"Evidence record '{record_id}' not found.")


@app.get("/challans", summary="List all issued challans", tags=["Challans"])
def list_challans(
    limit:  int = Query(50,  ge=1, le=500, description="Max challans to return"),
    offset: int = Query(0,   ge=0,          description="Skip this many challans (pagination)"),
):
    """Return the most recent N challan JSON payloads with image URLs attached."""
    all_files = sorted(CHALLAN_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    page      = all_files[offset: offset + limit]
    challans  = []
    for f in page:
        try:
            challans.append(_to_frontend_shape(json.loads(f.read_text())))
        except Exception as exc:
            log.warning("Skipping malformed challan JSON %s: %s", f.name, exc)
    return {"total": len(all_files), "offset": offset, "count": len(challans), "challans": challans}


@app.post(
    "/challans/{record_id}/review",
    summary="Update review status of a challan",
    tags=["Challans"],
)
def review_challan(record_id: str, body: ReviewRequest):
    """
    Patch the review_status of a saved challan.
    action: "approved" → AUTO_APPROVED | "rejected" → REJECTED | "escalated" → MANUAL_REVIEW
    """
    f = _find_challan_file(record_id)
    if f is None:
        raise HTTPException(404, detail=f"Challan '{record_id}' not found.")

    _ACTION_MAP = {
        "approved":  "AUTO_APPROVED",
        "rejected":  "REJECTED",
        "escalated": "MANUAL_REVIEW",
    }

    data = json.loads(f.read_text())
    data["review_status"] = _ACTION_MAP[body.action]
    data["review_notes"]  = body.notes
    data["reviewed_at"]   = datetime.now().isoformat()
    f.write_text(json.dumps(data, indent=2))

    log.info("Challan %s reviewed: %s", record_id, data["review_status"])
    return {"success": True, "record_id": record_id, "review_status": data["review_status"]}


@app.put(
    "/challans/{record_id}/violations",
    summary="Officer violation corrections + fine override",
    tags=["Challans"],
)
def update_violations(record_id: str, body: OfficerCorrection):
    """
    Persist officer-reviewed violation list and recalculated fine.

    Stores both:
    - ai_violations  — original AI detections (preserved for model retraining)
    - officer_violations — officer-approved set (used for challan issuance)

    violations[] is overwritten with the officer-approved list so that
    downstream consumers (Evidence Locker, report endpoint) read the
    final approved set without extra field logic.
    """
    f = _find_challan_file(record_id)
    if f is None:
        raise HTTPException(404, detail=f"Challan '{record_id}' not found.")

    data = json.loads(f.read_text())

    # Preserve original AI output before overwriting
    if not data.get("ai_violations"):
        data["ai_violations"] = body.ai_violations or data.get("violations", [])

    officer_violations_raw = [v.model_dump() for v in body.officer_violations]

    data["officer_violations"]  = officer_violations_raw
    data["violations"]          = officer_violations_raw   # canonical list
    data["total_fine"]          = body.officer_total_fine
    data["total_fine_inr"]      = body.officer_total_fine  # challan-shape alias
    data["officer_remark"]      = body.officer_remark
    data["officer_reviewed_at"] = datetime.now().isoformat()
    f.write_text(json.dumps(data, indent=2))

    log.info(
        "Challan %s violations updated by officer — %d violations, fine ₹%d",
        record_id, len(officer_violations_raw), body.officer_total_fine,
    )
    return {
        "success":                   True,
        "record_id":                 record_id,
        "officer_total_fine":        body.officer_total_fine,
        "officer_violations_count":  len(officer_violations_raw),
    }


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)