"""
detector.py
──────────────────────────────────────────────────────────────
Loads all YOLO models once at startup and provides scene detection
and per-vehicle expert pipelines.
 
traffic_yolo.pt class map (actual — verified from TRAFFIC_CLASSES /
model.names at load time, see [MODEL LOADED] log):
  0: person        1: motorcycle    2: car
  3: bus           4: truck         5: parking_zone
  6: autorickshaw
 
Separate expert models:
  helmet.pt        seatbelt.pt      triple_riding.pt
  phone.pt         traffic_light.pt zebra.pt
  license_plate.pt abnormal.pt      traffic_sign.pt   ← NEW
 
Note: parking_space.pt removed — parking handled by traffic_yolo.pt (class 5)
      autorickshaw treated same as car for violation checks
"""
 
import numpy as np
import cv2
from collections import defaultdict
from pathlib import Path
 
MODELS_DIR = Path(__file__).parent / "models"
 
 
# ── Model loader ──────────────────────────────────────────────────────────────
 
def _load(name: str, is_scene_model: bool = False):
    """Load a YOLO model; return None (demo mode) when weights are missing."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[WARN] ultralytics not installed — running in demo mode.")
        return None
    path = MODELS_DIR / name
    if not path.exists():
        print(f"[WARN] Missing model: {path}  →  demo mode for this agent.")
        return None
    model = YOLO(str(path))
    # Tag scene model so _run() can apply imgsz=1024 only to it
    model._hmates_is_scene_model = is_scene_model
    print(f"[MODEL LOADED] {name}  scene={is_scene_model}  classes={model.names}")
    return model
 
 
# ── Load all models once at import time ───────────────────────────────────────
 
traffic_model  = _load("traffic_yolo.pt", is_scene_model=True)  # main scene model (11 classes)
helmet_model   = _load("helmet.pt")
seatbelt_model = _load("seatbelt.pt")
triple_model   = _load("triple_riding.pt")
phone_model    = _load("phone.pt")
light_model    = _load("traffic_light.pt")
zebra_model    = _load("zebra.pt")
plate_model    = _load("license_plate.pt")
abnormal_model = _load("abnormal.pt")
sign_model     = _load("traffic_sign.pt")   # NEW — road sign detection
# parking_space.pt NOT needed — class 9 in traffic_yolo.pt covers it
 
 
# ── Class-ID maps ─────────────────────────────────────────────────────────────
# ALL maps verified against [MODEL LOADED] log output on 2026-06-21.
# DO NOT edit these without re-checking model.names at startup.

# traffic_yolo.pt — 7 classes (actual)
# Previously wrong: assumed 11 classes with helmet/no_helmet/license_plate etc.
TRAFFIC_CLASSES = {
    0: "person",
    1: "motorcycle",
    2: "car",
    3: "bus",
    4: "truck",
    5: "parking_zone",    # was "parking_space" — renamed in this weight
    6: "autorickshaw",
}

# helmet.pt — 3 classes (actual: Helmet / No-Helmet / person)
# _run() normalises to lowercase, so these are lowercase here too.
# Substring matching in bike_pipeline() handles "no-helmet" correctly.
HELMET_CLASSES = {0: "helmet", 1: "no-helmet", 2: "person"}

# seatbelt.pt — 2 classes (actual: Seat_Belt / WithoutSeat_Belt)
# Substring matching in car_pipeline() handles "withoutseat_belt" correctly.
SEATBELT_CLASSES = {0: "seat_belt", 1: "withoutseat_belt"}

# triple_riding.pt — 3 classes (actual order: double_rider / single_rider / triple_rider)
# Note: 0=double, 1=single — opposite of previous assumption.
TRIPLE_CLASSES = {0: "double_rider", 1: "single_rider", 2: "triple_rider"}

# phone.pt — 4 classes (actual: cigarettes / on-phone / phone / smoking)
# "on-phone" and "phone" both mean phone usage — handled in bike/car pipelines.
PHONE_CLASSES = {0: "cigarettes", 1: "on-phone", 2: "phone", 3: "smoking"}

# traffic_light.pt — 3 classes (actual: green / red / yellow)
# Note: red=1, NOT 0. Previous map had red=0 which caused wrong-signal detections.
LIGHT_CLASSES = {0: "green", 1: "red", 2: "yellow"}

# zebra.pt — 1 class (actual: ZebraCrossing → normalised to "zebracrossing")
ZEBRA_CLASSES = {0: "zebracrossing"}

# license_plate.pt — unchanged
PLATE_CLASSES = {0: "license_plate"}

# abnormal.pt — 5 classes (actual: Cigarette / Drinking / Eating / Phone / Seatbelt)
# This model detects driver behaviour, NOT driving pattern (no wrong_lane etc.)
# Normalised to lowercase by _run().
ABNORMAL_CLASSES = {
    0: "cigarette",
    1: "drinking",
    2: "eating",
    3: "phone",
    4: "seatbelt",
}

# traffic_sign.pt — 18 classes (actual, normalised to lowercase)
SIGN_CLASSES = {
    0:  "hazard",
    1:  "l",                    # left turn indicator — ignored for violations
    2:  "no entry",             # space in name — normalised to "no entry"
    3:  "r",                    # right turn indicator — ignored
    4:  "round-about",
    5:  "speed bump ahead",
    6:  "speed limit -100-",
    7:  "speed limit -60-",
    8:  "speed limit -70-",
    9:  "speed limit -80-",
    10: "speed limit 30",
    11: "stop",
    12: "do_not_turn_l",
    13: "do_not_turn_r",
    14: "green_traffic_light",
    15: "red_traffic_light",
    16: "yellow_traffic_light",
    17: "yield sign",
}

# Speed limit values keyed by normalised sign class name
SIGN_SPEED_LIMITS: dict[str, int] = {
    "speed limit 30":      30,
    "speed limit -60-":    60,
    "speed limit -70-":    70,
    "speed limit -80-":    80,
    "speed limit -100-":  100,
}

# Vehicles treated as "car" for seatbelt / phone / abnormal checks
CAR_LIKE = {"car", "bus", "truck", "autorickshaw"}
# Vehicles treated as "bike" for helmet / triple-riding checks
BIKE_LIKE = {"motorcycle"}
 
 
# ── Core inference runner ──────────────────────────────────────────────────────
 
def _run(model, img: np.ndarray, conf: float = 0.4) -> list:
    """
    Run YOLO inference; return list of detection dicts.
    Each dict: {class_id, class_name, conf, box:[x1,y1,x2,y2]}
    Returns [] in demo mode or on error.

    KEY FIXES:
    1. imgsz=1024 for the traffic scene model only, passed straight through
       to ultralytics rather than hand-resized first.
       Uploaded images (~430x436) drop a conf=0.142 car to 0 boxes at native
       resolution because YOLO's feature maps shrink below the car's footprint.
       Forcing imgsz=1024 reproduces the standalone test conditions where the
       car is reliably detected. A manual cv2.resize(img, (1024,1024)) used to
       sit here instead — that stretches non-square inputs instead of
       letterboxing them, which destroys small-object proportions and was
       itself silently killing detections. Passing imgsz=1024 to model()
       lets ultralytics do its own aspect-preserving letterbox (pad to
       square, don't stretch) and return boxes already rescaled to the
       original image — exactly what the standalone script does. Expert
       models (seatbelt, helmet, etc.) receive tight cropped ROIs and do
       NOT need this — left at default.

    2. class_name normalised to lowercase+stripped.
       Model weights may store class names as "Car", "Motorcycle", "WithoutSeat_Belt"
       etc. Bucket_map and substring checks use lowercase, so any capitalisation
       mismatch causes silent drops. Raw name preserved in class_name_raw for debug.
    """
    if model is None or img is None or img.size == 0:
        return []
    try:
        is_scene = getattr(model, '_hmates_is_scene_model', False)

        if is_scene:
            # BUGFIX: this used to manually cv2.resize(img, (1024, 1024))
            # under the theory that ultralytics "caches the inference
            # session at the first call's resolution" and silently ignores
            # imgsz= on later calls. That premise doesn't hold for a
            # YOLO(.pt) model — imgsz is a normal per-call argument, not
            # session-locked. The manual resize was also a non-aspect-
            # preserving STRETCH (forcing any input to a flat 1024x1024
            # square), not a letterbox — that distorts small-object
            # proportions enough to drop an already-marginal conf=0.142 car
            # to zero boxes. Passing imgsz=1024 straight through lets
            # ultralytics do its own aspect-preserving letterbox (pad to
            # square, don't stretch) — matching the standalone test script —
            # and it returns box coordinates already rescaled to the
            # original image, so no manual scale_x/scale_y back-transform
            # is needed.
            h, w = img.shape[:2]
            print(f"[_run] scene=True  conf={conf:.3f}  "
                  f"orig={w}x{h}  imgsz=1024 (letterboxed by ultralytics)")
            results = model(img, conf=conf, imgsz=1024, verbose=False)[0]
            scale_x = scale_y = 1.0
        else:
            print(f"[_run] scene=False  conf={conf:.3f}  img_shape={img.shape}")
            scale_x = scale_y = 1.0
            results = model(img, conf=conf, verbose=False)[0]

    except Exception as exc:
        print(f"[Model Error] {exc}")
        return []
    if results is None or results.boxes is None:
        return []
    print(f"[_run] raw_boxes={len(results.boxes)}")
    out = []
    for box in results.boxes:
        cls      = int(box.cls[0])
        conf_    = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        raw_name  = results.names.get(cls, str(cls))
        norm_name = raw_name.lower().strip()
        print(f"  det: cls={cls}  raw={raw_name!r}  norm={norm_name!r}  conf={conf_:.3f}")
        out.append({
            "class_id":       cls,
            "class_name":     norm_name,
            "class_name_raw": raw_name,
            "conf":           round(conf_, 3),
            "box":            [x1, y1, x2, y2],
        })
    return out
 
 
def _top(dets: list, class_map: dict) -> tuple:
    """Return (class_name, confidence) of highest-conf detection, or ('unknown', 0)."""
    if not dets:
        return "unknown", 0.0
    best = max(dets, key=lambda d: d["conf"])
    return class_map.get(best["class_id"], best["class_name"]), best["conf"]


def _run_classifier(model, img: np.ndarray) -> dict:
    """
    Run a YOLO *classification* model (results.probs), not a detection model
    (results.boxes). seatbelt.pt is trained as `yolo classify` — calling it
    through _run() always returned [] because _run() unconditionally reads
    results.boxes, which is None for a classifier. That's why seatbelt came
    back "unknown"/0.0 even when the model itself was confidently predicting
    WithoutSeat_Belt.

    A classifier has exactly one prediction per image, not a list of boxes,
    so this returns a single dict instead of a list:
        {class_id, class_name, class_name_raw, conf}
    Returns {} in demo mode, on error, on an empty image, or if the model
    turns out not to be a classifier (no .probs) — same fail-safe shape
    _run() uses ([] there, {} here, both falsy).
    """
    if model is None or img is None or img.size == 0:
        return {}
    try:
        results = model(img, verbose=False)[0]
        probs = results.probs
        if probs is None:
            print("[_run_classifier] results.probs is None — "
                  "this model doesn't look like a classifier.")
            return {}
        cls_id    = int(probs.top1)
        conf      = float(probs.top1conf)
        raw_name  = results.names.get(cls_id, str(cls_id))
        norm_name = raw_name.lower().strip()
        print(f"[_run_classifier] cls={cls_id}  raw={raw_name!r}  "
              f"norm={norm_name!r}  conf={conf:.3f}")
        return {
            "class_id":       cls_id,
            "class_name":     norm_name,
            "class_name_raw": raw_name,
            "conf":           round(conf, 3),
        }
    except Exception as exc:
        print(f"[Classifier Error] {exc}")
        return {}
 
 
def _crop(img: np.ndarray, box: list) -> np.ndarray:
    h, w = img.shape[:2]
    x1, y1, x2, y2 = box
    return img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]


def _dedupe(dets: list, iou_thresh: float = 0.5) -> list:
    """
    Tighter, same-class duplicate-box suppression on top of whatever
    ultralytics already did internally.

    ultralytics' built-in NMS (iou=0.7 by default, per class) only removes
    near-identical boxes. At the low conf=0.25 floor detect_scene() runs
    at, a single real motorcycle can still produce 2-3 surviving candidate
    boxes that overlap only ~40-50% (e.g. partial occlusion by the rider) —
    that's under the 0.7 IoU bar so ultralytics keeps both. Each surviving
    "ghost" box then gets its own bike_pipeline() call downstream, so one
    real bike can silently become 2-3 independent phone/helmet/triple-riding
    rolls. Re-running suppression here at a looser iou_thresh (0.5) catches
    those before they're bucketed for the per-vehicle expert pipelines.
    """
    if not dets:
        return []

    by_class: dict[str, list] = defaultdict(list)
    for d in dets:
        by_class[d["class_name"]].append(d)

    keep: list = []
    for cls_dets in by_class.values():
        cls_dets = sorted(cls_dets, key=lambda d: d["conf"], reverse=True)
        suppressed = [False] * len(cls_dets)
        for i, di in enumerate(cls_dets):
            if suppressed[i]:
                continue
            keep.append(di)
            for j in range(i + 1, len(cls_dets)):
                if not suppressed[j] and boxes_overlap(di["box"], cls_dets[j]["box"], iou_thresh):
                    suppressed[j] = True
    return keep
 
 
# ── Level 1: Scene Understanding ──────────────────────────────────────────────
 
def detect_scene(img: np.ndarray, conf: float = 0.05) -> dict:
    """
    Run traffic_yolo.pt and bucket detections by vehicle type.
 
    Returns:
        {cars, bikes, persons, trucks, buses, autorickshaws,
         parking_spaces, all}
    """

    all_det = _run(traffic_model, img, conf)
    all_det = _dedupe(all_det, iou_thresh=0.5)
    print("\n=== RAW DETECTIONS ===")
    for d in all_det:
        print(d)
    scene = {
        "cars":           [],
        "bikes":          [],
        "persons":        [],
        "trucks":         [],
        "buses":          [],
        "autorickshaws":  [],
        "parking_spaces": [],
        "all":            all_det,
    }
 
    bucket_map = {
        # All keys are lowercase to match _run()'s normalised class_name output
        "car":              "cars",
        "motorcycle":       "bikes",
        "motorbike":        "bikes",
        "bike":             "bikes",
        "person":           "persons",
        "pedestrian":       "persons",
        "truck":            "trucks",
        "bus":              "buses",
        "autorickshaw":     "autorickshaws",
        "auto":             "autorickshaws",
        "auto-rickshaw":    "autorickshaws",
        "parking_zone":     "parking_spaces",   # actual class name in traffic_yolo.pt
        "parking_space":    "parking_spaces",   # keep for forward compat
        "parking space":    "parking_spaces",
        "parkingspace":     "parking_spaces",
    }

    for d in all_det:
        b = bucket_map.get(d["class_name"])
        if b:
            scene[b].append(d)
        else:
            # Suppress noise for known non-vehicle classes from traffic_yolo.pt
            _known_non_vehicle = {
                "license_plate", "traffic_light", "helmet", "no_helmet",
                "no-helmet", "parking_zone", "license plate", "traffic light",
            }
            if d["class_name"] not in _known_non_vehicle:
                print(f"[detect_scene] UNMAPPED: norm={d['class_name']!r} "
                      f"raw={d.get('class_name_raw','?')!r}  conf={d['conf']:.3f}"
                      f"  → add to bucket_map if this is a vehicle")

    print(f"[detect_scene] cars={len(scene['cars'])}  bikes={len(scene['bikes'])}  "
          f"persons={len(scene['persons'])}  trucks={len(scene['trucks'])}  "
          f"buses={len(scene['buses'])}  autos={len(scene['autorickshaws'])}")
 
    return scene
 
 
def bike_pipeline(img: np.ndarray, bike_box: list) -> dict:
    """
    Expert pipeline for a single motorcycle ROI.
    Checks: helmet, triple riding, phone usage, plate.
    Returns:
        {helmet, helmet_conf, triple_riding, triple_conf,
         phone, phone_conf, plate, raw}
    """
    x1, y1, x2, y2 = bike_box
    h, w = img.shape[:2]

    # Pad the crop so rider heads/hands aren't cut off by a tight bike box.
    pad_x = int((x2 - x1) * 0.25)
    pad_y = int((y2 - y1) * 0.50)
    px1 = max(0, x1 - pad_x)
    py1 = max(0, y1 - pad_y)
    px2 = min(w, x2 + pad_x)
    py2 = min(h, y2 + pad_y)

    roi = img[py1:py2, px1:px2]
    if roi.size == 0:
        return {}

    # Phone-usage detection gets its own, tighter crop. The 25%/50% padding
    # above exists so helmet/triple-riding checks can see the rider's head
    # and any passengers — but that same wide crop also pulls in hands,
    # shoulders, and shadows outside the bike that the phone model was
    # false-firing on. Use a much smaller margin here instead.
    PHONE_PAD_X_RATIO = 0.10
    PHONE_PAD_Y_RATIO = 0.15
    phone_pad_x = int((x2 - x1) * PHONE_PAD_X_RATIO)
    phone_pad_y = int((y2 - y1) * PHONE_PAD_Y_RATIO)
    qx1 = max(0, x1 - phone_pad_x)
    qy1 = max(0, y1 - phone_pad_y)
    qx2 = min(w, x2 + phone_pad_x)
    qy2 = min(h, y2 + phone_pad_y)
    phone_roi = img[qy1:qy2, qx1:qx2]

    h_dets  = _run(helmet_model, roi)
    t_dets  = _run(triple_model, roi)
    p_dets  = _run(phone_model,  phone_roi) if phone_roi.size > 0 else []
    pl_dets = _run(plate_model,  roi)

    # Helmet: model classes are "helmet" (0), "no-helmet" (1), "person" (2)
    # after _run() normalisation. Match "no-helmet" or any "no"+"helmet" variant.
    NO_HELMET_CONF_THRESH = 0.40
    no_helmet_dets = [
        d for d in h_dets
        if ("no" in d.get("class_name", "") and "helmet" in d.get("class_name", ""))
        and d.get("conf", 0.0) >= NO_HELMET_CONF_THRESH
    ]

    if no_helmet_dets:
        h_cls  = "no_helmet"
        h_conf = max(d["conf"] for d in no_helmet_dets)
    elif h_dets:
        best   = max(h_dets, key=lambda d: d.get("conf", 0.0))
        h_cls  = best.get("class_name", "unknown")
        h_conf = best.get("conf", 0.0)
    else:
        h_cls, h_conf = "unknown", 0.0

    t_cls, t_conf = _top(t_dets, TRIPLE_CLASSES)

    # Phone: model classes are "cigarettes"(0),"on-phone"(1),"phone"(2),"smoking"(3)
    # "on-phone" and "phone" both indicate phone usage. Cigarettes/smoking → not phone.
    phone_dets = [
        d for d in p_dets
        if d.get("class_name", "") in ("on-phone", "phone")
    ]
    if phone_dets:
        p_cls  = "phone"
        p_conf = max(d["conf"] for d in phone_dets)
    else:
        p_cls, p_conf = "no_phone", 0.0

    return {
        "helmet":        h_cls,  "helmet_conf":  round(h_conf, 3),
        "triple_riding": t_cls,  "triple_conf":  round(t_conf, 3),
        "phone":         p_cls,  "phone_conf":   round(p_conf, 3),
        "plate":         pl_dets,
        "raw": {
            "helmet": h_dets, "triple": t_dets,
            "phone":  p_dets, "plate":  pl_dets,
        },
    }
def car_pipeline(img: np.ndarray, car_box: list) -> dict:
    """
    Expert pipeline for car / truck / bus / autorickshaw ROI.
 
    Checks: seatbelt, phone usage, abnormal behaviour, plate.
    Returns:
        {seatbelt, seatbelt_conf, phone, phone_conf,
         abnormal, abnormal_conf, plate, raw}
    """
    roi = _crop(img, car_box)
    if roi.size == 0:
        return {}
    cv2.imwrite("debug_car_crop.jpg", roi)
    print("[DEBUG] Saved car crop:", roi.shape)

    # BUGFIX: seatbelt.pt is a classification model (yolo classify), not a
    # detection model — it has no boxes, only results.probs (a single
    # top1/top1conf prediction over the whole ROI). Running it through
    # _run() always came back [] because _run() unconditionally reads
    # results.boxes. Use _run_classifier() instead — see that function's
    # docstring.
    seatbelt_pred = _run_classifier(seatbelt_model, roi)
    p_dets  = _run(phone_model,    roi)
    pl_dets = _run(plate_model,    roi)
    ab_dets = _run(abnormal_model, roi)

    # ── Seatbelt: read the classifier's single top-1 prediction ────────────────
    # seatbelt.pt's actual classes are Seat_Belt / WithoutSeat_Belt (see
    # SEATBELT_CLASSES). Substring matching kept for label-name robustness —
    # same reasoning as the old detection-list version, just reading from a
    # single classifier prediction instead of a (always-empty) detection list.
    NO_SEATBELT_CONF_THRESH = 0.40  # pre-filter floor before fusing
    sb_name = seatbelt_pred.get("class_name", "")
    sb_conf = seatbelt_pred.get("conf", 0.0)
    is_no_seatbelt = (
        ("without" in sb_name or
         ("no" in sb_name and "no_" in sb_name))
        and "seat" in sb_name
    )

    if is_no_seatbelt and sb_conf >= NO_SEATBELT_CONF_THRESH:
        s_cls  = "no_seatbelt"
        s_conf = sb_conf
    elif seatbelt_pred:
        # Positive "Seat_Belt" / "seatbelt" prediction — no violation
        s_cls  = sb_name or "unknown"
        s_conf = sb_conf
    else:
        s_cls, s_conf = "unknown", 0.0

    # Phone: same logic as bike_pipeline — "on-phone" and "phone" = violation
    phone_dets = [
        d for d in p_dets
        if d.get("class_name", "") in ("on-phone", "phone")
    ]
    if phone_dets:
        p_cls  = "phone"
        p_conf = max(d["conf"] for d in phone_dets)
    else:
        p_cls, p_conf = "no_phone", 0.0

    # Abnormal: actual classes are cigarette/drinking/eating/phone/seatbelt.
    # Any detection = distracted driving violation. "seatbelt" here means the
    # model sees a seatbelt-related behaviour (cross-check with seatbelt model).
    # We report the highest-confidence non-seatbelt class as the abnormal type.
    ab_dets_filtered = [d for d in ab_dets if d.get("class_name") != "seatbelt"]
    if ab_dets_filtered:
        best    = max(ab_dets_filtered, key=lambda d: d.get("conf", 0.0))
        ab_cls  = best.get("class_name", "unknown")
        ab_conf = best.get("conf", 0.0)
    elif ab_dets:
        best    = max(ab_dets, key=lambda d: d.get("conf", 0.0))
        ab_cls  = best.get("class_name", "unknown")
        ab_conf = best.get("conf", 0.0)
    else:
        ab_cls, ab_conf = "normal", 0.0

    return {
        "seatbelt":      s_cls,  "seatbelt_conf":  round(s_conf,  3),
        "phone":         p_cls,  "phone_conf":     round(p_conf,  3),
        "abnormal":      ab_cls, "abnormal_conf":  round(ab_conf, 3),
        "plate":         pl_dets,
        "raw": {
            "seatbelt": seatbelt_pred, "phone":    p_dets,
            "abnormal": ab_dets,       "plate":    pl_dets,
        },
    }
 
 
def pedestrian_pipeline(img: np.ndarray, person_box: list) -> dict:
    """Minimal pipeline — spatial checks handled by rule engine."""
    return {"person_box": person_box}
 
 
def signal_pipeline(img: np.ndarray) -> dict:
    """
    Shared scene-level pipeline (run once per frame, not per vehicle).

    Returns:
        {signal_color, signal_conf, zebra_detected, zebra_boxes, light_boxes}

    FIXED: traffic_light.pt actual classes: {0:'green', 1:'red', 2:'yellow'}
    Previous LIGHT_CLASSES had red=0, green=1 — inverted. _run() normalises
    class_name to lowercase so we can match directly by class_name string
    rather than relying on the class_id→LIGHT_CLASSES lookup.
    """
    light_dets = _run(light_model, img)
    zebra_dets = _run(zebra_model, img)

    # Match signal colour by class_name string (already normalised to lowercase)
    # so we're immune to class_id ordering differences across weight files.
    sig_cls, sig_conf = "unknown", 0.0
    if light_dets:
        # Priority: red > yellow > green (safety)
        for colour in ("red", "yellow", "green"):
            matches = [d for d in light_dets if d["class_name"] == colour]
            if matches:
                best = max(matches, key=lambda d: d["conf"])
                sig_cls  = colour
                sig_conf = best["conf"]
                break

    return {
        "signal_color":   sig_cls,
        "signal_conf":    round(sig_conf, 3),
        "zebra_detected": len(zebra_dets) > 0,
        "zebra_boxes":    zebra_dets,
        "light_boxes":    light_dets,
    }
 
 
def parking_pipeline(img: np.ndarray) -> dict:
    """
    Parking detection using traffic_yolo.pt class 9 (parking_space).

    A detected parking_space box = a marked parking zone.
    Used by rule_engine to check if a stationary vehicle is
    parked illegally (outside a marked zone).

    Returns:
        {parking_dets, parking_zone_boxes}

    BUGFIX: was calling _run(traffic_model, img) with default conf=0.4.
    Two problems with that:
      1. conf=0.4 > car confidence (0.142), so this call was triggering the
         scene model at the wrong threshold — wasting inference time and
         potentially locking the YOLO session at native resolution before
         detect_scene() got to run its 1024-resize path.
      2. parking_space detections are rare and often low-confidence; 0.4 was
         silently dropping them. Use 0.05 to match detect_scene().
    """
    all_det = _run(traffic_model, img, conf=0.05)
    parking_dets = [d for d in all_det
                    if d["class_name"] in ("parking_zone", "parking_space")]
    return {
        "parking_dets":      parking_dets,
        "parking_zone_boxes": parking_dets,   # marked legal parking zones
        # NOTE: rule_engine checks if vehicle is OUTSIDE these zones
        "no_parking_zones":  [],              # kept for API compatibility
    }
 
 
def traffic_sign_pipeline(img: np.ndarray) -> dict:
    """
    Shared scene-level road sign detection (run once per frame).

    Uses traffic_sign.pt (18 classes — actual names verified from model log).
    Matches by class_name string (normalised lowercase) so class_id ordering
    changes in future weights don't break detection.

    Returns:
        {sign_dets, active_signs, speed_limit_kmh, stop_sign,
         no_entry, roundabout, hazard}
    """
    sign_dets = _run(sign_model, img)

    active_signs: set[str] = set()
    for d in sign_dets:
        # class_name already normalised to lowercase by _run()
        active_signs.add(d["class_name"])

    # Speed limits — match by substring "speed limit" in class_name
    speed_limit_kmh: int | None = None
    for d in sign_dets:
        cn = d["class_name"]   # e.g. "speed limit 30", "speed limit -80-"
        for norm_name, limit in SIGN_SPEED_LIMITS.items():
            if cn == norm_name:
                if speed_limit_kmh is None or limit < speed_limit_kmh:
                    speed_limit_kmh = limit

    return {
        "sign_dets":       sign_dets,
        "active_signs":    active_signs,
        "speed_limit_kmh": speed_limit_kmh,
        "stop_sign":       "stop"       in active_signs,
        "no_entry":        "no entry"   in active_signs,   # actual: "no entry" (with space)
        "roundabout":      "round-about" in active_signs,  # actual: "round-about"
        "hazard":          "hazard"     in active_signs,
    }
 
 
def detect_plates_on_vehicle(img: np.ndarray, vehicle_box: list) -> list:
    """
    Run license_plate.pt on a vehicle ROI (only after a violation confirmed).
    Restores absolute image coordinates before returning.
    """
    roi = _crop(img, vehicle_box)
    if roi.size == 0:
        return []
    plates = _run(plate_model, roi)
    xo, yo = vehicle_box[0], vehicle_box[1]
    for p in plates:
        p["box"] = [
            p["box"][0] + xo, p["box"][1] + yo,
            p["box"][2] + xo, p["box"][3] + yo,
        ]
    return plates

# ── Geometry utilities ────────────────────────────────────────────────────────

def box_center(box: list) -> tuple:
    return ((box[0] + box[2]) // 2, (box[1] + box[3]) // 2)
 
 
def vehicle_inside_box(vehicle_box: list, region_box: list) -> bool:
    """True if the vehicle's centre point falls inside region_box."""
    cx, cy = box_center(vehicle_box)
    x1, y1, x2, y2 = region_box
    return x1 <= cx <= x2 and y1 <= cy <= y2
 
 
def vehicle_outside_parking_zones(vehicle_box: list,
                                  parking_zones: list) -> bool:
    """
    True if the vehicle centre does NOT fall inside ANY marked parking zone.
    Used by rule_engine for illegal parking detection.
    """
    if not parking_zones:
        return False   # no zones detected → can't confirm illegal parking
    cx, cy = box_center(vehicle_box)
    for z in parking_zones:
        x1, y1, x2, y2 = z["box"]
        if x1 <= cx <= x2 and y1 <= cy <= y2:
            return False   # inside a legal zone → not illegal
    return True            # outside all zones → illegal
 
def boxes_overlap(a: list, b: list, threshold: float = 0.05) -> bool:
    """True if IoU(a, b) >= threshold."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return False
    inter  = (ix2 - ix1) * (iy2 - iy1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union  = area_a + area_b - inter
    return (inter / union) >= threshold if union > 0 else False