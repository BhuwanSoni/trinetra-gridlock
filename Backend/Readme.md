# HMATES — Hierarchical Multi-Agent Traffic Enforcement & Automated Challan System

> AI-powered traffic violation detection, evidence capture, and automated challan generation using computer vision and multi-agent reasoning.

---

## Architecture Overview

```
Input Image / Video Feed
          ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1 · Image Enhancement                                    │
│  CLAHE · Gaussian Denoise · Unsharp Mask · Brightness Norm      │
│  preprocess.py                                                  │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2 · Traffic Scene Understanding                          │
│  YOLO11 (traffic_yolo.pt) — 11-class scene model               │
│  DeepSORT — persistent IDs across frames (Car#17, Bike#22)      │
│  detector.detect_scene() + tracker.update_tracks()             │
└──────────┬──────────────┬──────────────────┬────────────────────┘
           ↓              ↓                  ↓
┌──────────────┐  ┌───────────────┐  ┌─────────────────────────┐
│  Layer 3a    │  │  Layer 3b     │  │  Layer 3c               │
│  Bike Agent  │  │  Car Agent    │  │  Scene Agents           │
│  helmet.pt   │  │  seatbelt.pt  │  │  traffic_light.pt       │
│  triple.pt   │  │  phone.pt     │  │  zebra.pt               │
│  phone.pt    │  │  abnormal.pt  │  │  traffic_sign.pt        │
│  plate.pt    │  │  plate.pt     │  │  parking (class 9)      │
└──────┬───────┘  └───────┬───────┘  └──────────┬──────────────┘
       └──────────────────┼───────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 4 · Rule-Based Reasoning Engine (v2)                     │
│  Confidence Fusion     final = 0.75·model + 0.25·scene          │
│  Consecutive-Frame Gate  N frames must confirm before flagging  │
│  Violation Severity    Critical / High / Medium / Low           │
│  Review Queue          AUTO_APPROVED / MANUAL_REVIEW / REJECTED │
│  UNKNOWN Plate Guard   no auto-challan without readable plate   │
│  Wrong-Side Detection  trajectory angle vs road direction        │
│  Parking Rule          outside marked zone + 120 stationary fr. │
│  Traffic Sign Rules    No Entry · Stop Sign · Overspeeding      │
│  Multi-Violation Fusion  one fused record per vehicle           │
│  Emergency Vehicle Guard  AMBU / FIRE / POLICE plates exempt    │
│  rule_engine.py                                                 │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 5 · Evidence · OCR · Analytics · Challan · API           │
│  Conditional OCR     plate read only after violation confirmed  │
│  PaddleOCR (primary, 85–95%) + EasyOCR (fallback, 70–85%)      │
│  Evidence Crops      full frame + vehicle crop + plate crop     │
│  XGBoost Risk AI     ML-predicted risk score per vehicle        │
│  Streamlit Dashboard  live KPIs · charts · Jaipur map hotspots  │
│  FastAPI REST Layer  /upload · /report · /search · /challans    │
│  plate_ocr.py · evidence.py · analytics.py · risk_ai.py        │
│  dashboard.py · api.py                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Violations Detected

| Violation | Severity | Risk | Fine | Auto-Challan Threshold |
|-----------|----------|------|------|------------------------|
| Red Light Violation | Critical | 95 | ₹5,000 | 83% |
| Wrong Side Driving | Critical | 90 | ₹5,000 | 90% |
| No Entry Violation | Critical | 88 | ₹5,000 | 88% |
| Triple Riding | High | 85 | ₹1,000 | 88% |
| Abnormal Driving Behaviour | High | 80 | ₹2,000 | 90% |
| Mobile Usage While Driving | High | 78 | ₹5,000 | 92% |
| Overspeeding | High | 75 | ₹2,000 | 88% |
| Helmet Violation | Medium | 70 | ₹1,000 | 83% |
| Seat Belt Violation | Medium | 65 | ₹1,000 | 85% |
| Stop Line / Zebra Violation | Medium | 60 | ₹1,000 | 80% |
| Stop Sign Violation | Medium | 58 | ₹1,000 | 85% |
| Illegal Parking | Low | 40 | ₹500 | 78% |
| Pedestrian Signal Violation | Low | 35 | ₹200 | 78% |

> **Emergency vehicles** — plates matching `AMBU*`, `FIRE*`, `POLICE*`, `ARMY*`, `NAVY*`, `AIRFO*` are never challaned and are excluded from all analytics.

---

## Review Queue

Every violation is assigned one of three statuses before a challan is issued.

```
fused confidence
      │
      ├── < 0.65          → REJECTED       (silent drop, not recorded)
      │
      ├── 0.65 – threshold → MANUAL_REVIEW  (queued for human reviewer)
      │                                     (also forced when plate = UNKNOWN)
      │
      └── ≥ threshold     → AUTO_APPROVED  (challan issued automatically)
```

Consecutive-frame requirements before a violation can be raised (video mode):

| Violation | Frames required |
|-----------|----------------|
| Mobile Usage While Driving | 5 |
| Seat Belt / Wrong Side / Abnormal | 4 |
| Helmet / Triple Riding / No Entry / Stop Sign | 3 |
| Red Light / Zebra / Overspeeding | 2 |

Single-image mode bypasses the frame gate automatically.

---

## Improvements

| # | Improvement | File(s) |
|---|-------------|---------|
| 1 | **Vehicle Tracking** — DeepSORT persistent IDs across frames | `tracker.py` |
| 2 | **Abnormal Behaviour** — `abnormal.pt` model (wrong lane, sudden stop, U-turn, reverse, reckless) | `detector.py`, `rule_engine.py` |
| 3 | **Conditional OCR** — plate read only after a violation is confirmed | `main.py` |
| 4 | **Confidence Fusion** — `0.75×model + 0.25×scene` | `rule_engine.py` |
| 5 | **Violation Severity** — Critical / High / Medium / Low + risk score 0–100 | `rule_engine.py` |
| 6 | **Parking Detection** — parking_space class (traffic_yolo.pt) + 120-frame stationary gate | `detector.py`, `rule_engine.py`, `tracker.py` |
| 7 | **Wrong-Side Driving** — trajectory angle vs road direction, confidence scaled by trajectory length | `tracker.py`, `rule_engine.py` |
| 8 | **Evidence Crops** — vehicle_crop.jpg + plate_crop.jpg saved per incident | `evidence.py` |
| 9 | **Streamlit Dashboard** — live KPIs, charts, Jaipur GPS map, repeat offenders | `dashboard.py` |
| 10 | **Multi-Violation Fusion** — all violations per vehicle merged into one record | `rule_engine.py`, `main.py` |
| ★ | **Consecutive-Frame Gate** — N consecutive detections required before flagging (v2) | `rule_engine.py` |
| ★ | **UNKNOWN Plate Guard** — no auto-challan when plate is unreadable (v2) | `rule_engine.py`, `main.py` |
| ★ | **Review Queue Tiers** — AUTO_APPROVED / MANUAL_REVIEW / REJECTED (v2) | `rule_engine.py`, `main.py` |
| ★ | **Traffic Sign Rules** — No Entry, Stop Sign, Overspeeding from `traffic_sign.pt` | `detector.py`, `rule_engine.py` |
| ★ | **XGBoost Risk AI** — ML-predicted risk score replaces rule-table risk | `risk_ai.py` |
| ★ | **PaddleOCR** — primary OCR engine (85–95% on Indian plates); EasyOCR fallback | `plate_ocr.py` |
| ★ | **FastAPI REST Layer** — deployable microservice with async video processing | `api.py` |
| ★ | **Emergency Vehicle Guard** — prefix-based plate filter for exempt vehicles | `rule_engine.py` |

---

## Directory Structure

```
hmates/
├── models/
│   ├── traffic_yolo.pt       # 11-class scene model (includes parking_space)
│   ├── helmet.pt
│   ├── seatbelt.pt
│   ├── triple_riding.pt
│   ├── phone.pt
│   ├── traffic_light.pt
│   ├── zebra.pt
│   ├── license_plate.pt
│   ├── abnormal.pt
│   └── traffic_sign.pt       # stop · speed limits · no_entry · hazard
├── evidence/
│   ├── images/               # full frame + vehicle crop + plate crop
│   ├── metadata/             # JSON per incident
│   └── challans/             # JSON per challan
├── detectors/
│   ├── preprocess.py
│   ├── detector.py
│   └── tracker.py
├── intelligence/
│   ├── rule_engine.py
│   └── risk_ai.py
├── ocr/
│   └── plate_ocr.py
├── evidence/
│   └── evidence.py
├── analytics/
│   └── analytics.py
├── main.py
├── dashboard.py
├── api.py
└── requirements.txt
```

---

## Installation

```bash
pip install -r requirements.txt
```

Key dependencies: `ultralytics`, `deep-sort-realtime`, `paddleocr`, `easyocr`, `fastapi`, `streamlit`, `xgboost`, `opencv-python`

---

## Usage

```bash
# Single image
python main.py --image traffic_photo.jpg --camera CAM-03 --location "MG Road, Jaipur"

# Single image with known speed (km/h) for overspeeding check
python main.py --image photo.jpg --speed 85

# Video file (tracking + deduplication + speed estimation)
python main.py --video footage.mp4 --camera CAM-01 --location "Tonk Road"

# Video with live annotated display
python main.py --video footage.mp4 --display

# Analytics report from saved evidence
python main.py --report

# Streamlit dashboard
python main.py --dashboard
# or: streamlit run dashboard.py

# FastAPI server
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Demo (no model files required)
python main.py --demo
```

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload` | Process image → violations + challan |
| POST | `/upload/video` | Async video processing (returns `job_id`) |
| GET | `/status/{job_id}` | Poll async video job |
| GET | `/report` | Full analytics report |
| GET | `/search/plate/{plate}` | Records by number plate |
| GET | `/search/date/{date}` | Records by date (`YYYY-MM-DD`) |
| GET | `/search/camera/{cam_id}` | Records by camera |
| GET | `/search/violation/{vtype}` | Records by violation type |
| GET | `/challans` | Recent challans |
| GET | `/health` | Liveness check |

---

## Performance

| Component | Speed | Hardware |
|-----------|-------|----------|
| YOLO11n (scene) | ~28 FPS | RTX 3050 6 GB |
| YOLO11m (scene) | ~14 FPS | RTX 3050 6 GB |
| PaddleOCR | ~120 ms/plate | CPU |
| EasyOCR (fallback) | ~180 ms/plate | CPU |
| DeepSORT tracking | ~8 ms/frame | CPU |
| Full pipeline (image) | ~250–400 ms | All expert agents |

> Wrong-side driving and illegal parking require **video mode** — both depend on multi-frame trajectory/stationary history. They are skipped automatically in single-image mode.

---

## Challan Example

```
══════════════════════════════════════════════════════════════
  CHALLAN  CHN-A1B2C3D4  ·  HIGH RISK (82/100)  ·  AUTO_APPROVED
══════════════════════════════════════════════════════════════
  Plate    : RJ14AB1234
  Location : MG Road, Jaipur  ·  Camera: CAM-03
──────────────────────────────────────────────────────────────
  [Critical] Red Light Violation         ₹5,000  Risk:95  Conf:91%
  [High    ] Triple Riding               ₹1,000  Risk:85  Conf:88%
  [Medium  ] Helmet Violation            ₹1,000  Risk:70  Conf:93%
──────────────────────────────────────────────────────────────
  TOTAL FINE    : ₹7,000
  COMBINED RISK : 82/100  [High]
  REVIEW STATUS : AUTO_APPROVED
══════════════════════════════════════════════════════════════
```

---

## Key Design Decisions

**Hierarchical inference** — the main YOLO model runs once per frame; expert models operate on vehicle ROIs only, cutting total inference time by ~40%.

**Lazy plate extraction** — OCR triggers only after a violation is confirmed, saving 30–40% of OCR calls. Challans against UNKNOWN plates always go to manual review.

**Consecutive-frame gate** — a single frame cannot trigger a challan in video mode. Noisy detections (phone, seatbelt) require up to 5 consecutive confirmations before the violation is raised, dramatically reducing false positives.

**Three-tier review queue** — violations are not binary accepted/rejected. Every output carries AUTO_APPROVED, MANUAL_REVIEW, or REJECTED status, enabling a human reviewer workflow between the model and the legal challan.

**Trajectory-scaled confidence** — wrong-side driving confidence ramps up with trajectory length. A vehicle tracked for 3 frames cannot produce a high-confidence wrong-side flag.

**Deterministic rule engine** — all logic between raw model outputs and challan generation is explicit, auditable Python. The pipeline is defensible in court because every decision has a traceable reason.

**XGBoost risk scoring** — the fixed risk table is replaced by an ML-predicted score that incorporates violation type, vehicle class, speed, and multi-violation combinations for a more realistic severity estimate.