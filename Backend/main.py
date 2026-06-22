"""
main.py
──────────────────────────────────────────────────────────────
HMATES — Hierarchical Multi-Agent Traffic Enforcement
         & Automated Challan System  (UPGRADED v2)

5-Layer Architecture
  Layer 1  Image Enhancement          (preprocess.py)
  Layer 2  Traffic Scene Understanding (detector.py)
  Layer 3  Expert Violation Agents    (detector.py pipelines)
  Layer 4  Rule-Based Reasoning Engine (rule_engine.py)
  Layer 5  Evidence, OCR, Auto-Challan (evidence.py + plate_ocr.py)

New in v2
  • UNKNOWN-plate guard — challans only auto-issued when plate is readable
  • Review queue tiers — AUTO_APPROVED / MANUAL_REVIEW in every challan
  • reset_confirmation_state() called between videos / test runs
  • Consecutive-frame gate active (rule_engine.confirm_violation)
  • illegal parking threshold raised to 120 frames in rule_engine

Usage (unchanged):
    python main.py --image  path.jpg  [--camera CAM-01] [--location "MG Road"]
    python main.py --video  path.mp4  [--display]
    python main.py --report
    python main.py --demo
    python main.py --dashboard
"""

import argparse
import sys
import itertools
import cv2
import numpy as np
from collections import defaultdict
from pathlib import Path

from detectors.preprocess   import enhance_array, load_image
from detectors.detector     import (detect_scene, bike_pipeline, car_pipeline,
                                    pedestrian_pipeline, signal_pipeline,
                                    parking_pipeline, detect_plates_on_vehicle,
                                    traffic_sign_pipeline)
from intelligence.rule_engine import (evaluate_bike, evaluate_car,
                                      evaluate_pedestrian,
                                      fuse_vehicle_violations,
                                      summarize_violations,
                                      reset_confirmation_state,
                                      apply_plate,
                                      ReviewStatus)
from ocr.plate_ocr          import extract_plate_from_image
from evidence.evidence      import (annotate_image, create_evidence_record,
                                    save_evidence, save_evidence_images,
                                    write_evidence_metadata, generate_challan)
from analytics.analytics    import (generate_summary_report,
                                    print_report, save_report)
from detectors.tracker      import update_tracks, is_stationary
from intelligence.risk_ai   import predict_risk
from firebase.storage   import upload_evidence_pack
from firebase.firestore import push_to_firestore


# ── OCR helper (Improvement #3 — lazy, called only after violation confirmed) ─

def _resolve_plate(raw_img: np.ndarray, enhanced_img: np.ndarray,
                   vehicle_box: list) -> tuple[str, list, list | None]:
    """
    Detect plates, then OCR.  Returns ("UNKNOWN", [], None) on any failure.
    Only called AFTER at least one violation candidate has been raised.

    BUGFIX: plate detection now runs on raw_img (see process_frame()'s Layer 1
    note — enhance_array() was suppressing marginal YOLO detections), while
    OCR still reads from enhanced_img, where CLAHE/sharpening genuinely help
    character legibility instead of hurting box detection. Box coordinates
    are valid for both — enhancement doesn't shift pixel positions, only
    contrast/sharpness.
    """
    plate_dets = detect_plates_on_vehicle(raw_img, vehicle_box)
    if not plate_dets:
        return "UNKNOWN", [], None
    plate_info = extract_plate_from_image(enhanced_img, plate_dets)
    plate_box  = plate_dets[0]["box"]
    return plate_info["plate_text"], plate_dets, plate_box


# ── Single-frame pipeline ──────────────────────────────────────────────────────

def process_frame(img: np.ndarray,
                  camera_id:      str   = "CAM-01",
                  location:       str   = "Unknown",
                  save:           bool  = True,
                  road_direction: tuple = (1, 0),
                  speed_kmh:      float = 0.0,
                  is_video:       bool  = False) -> dict:
    """
    Complete 5-layer HMATES pipeline on a single frame.

    Args:
        is_video: True when called as part of a video stream (process_video()).
            Enables DeepSORT tracking and the consecutive-frame confirmation
            gate. False (default) for single-image uploads — tracking is
            skipped entirely and every detection gets track_id = -1, which
            makes confirm_violation() bypass the multi-frame requirement
            (a single image has no "next frame" to confirm against, so
            requiring 3 consecutive frames would silently reject every
            violation no matter how confident the detection — this was the
            cause of single-image uploads always returning 0 violations).

    Returns dict: {scene, violations, challans, summary, sign_data}
    """

    # Layer 1 — Image Enhancement
    # BUGFIX: enhance_array() (CLAHE + Gaussian denoise + a strong 1.5x/-0.5x
    # unsharp-mask sharpen + brightness min-max stretch) used to run before
    # EVERY detection call below. The standalone test script that reliably
    # finds cars down to conf=0.142 runs YOLO on the raw, untouched upload —
    # that 0.142 is already marginal, and CLAHE + aggressive sharpening is
    # enough to shift feature-map activations on a small (~430x436) image
    # past the point where the model stops firing entirely, producing the
    # raw_boxes=0 symptom on identical weights, identical image content, and
    # identical imgsz=1024. enhance_array()'s output is now kept ONLY for
    # the saved evidence image/crops (and plate OCR legibility) below —
    # cosmetic uses where contrast/sharpening genuinely help a human
    # reviewer instead of suppressing the detector.
    raw_img      = img
    enhanced_img = enhance_array(img)

    # Layer 2 — Scene Understanding (raw image — see note above)
    scene = detect_scene(raw_img)
    print("Bikes:", len(scene["bikes"]))
    print("Cars:", len(scene["cars"]))
    print("Persons:", len(scene["persons"]))

    # Improvement #1: persistent vehicle IDs via DeepSORT
    # BUGFIX: only run the tracker in video mode. Running it on a lone
    # uploaded image assigned real (non -1) track IDs, which meant the
    # consecutive-frame gate in rule_engine.confirm_violation() required 3
    # confirmations that a single image could never produce.
    if is_video:
        all_tracked = update_tracks(scene["all"], img)
        tracked_map = {(d["box"][0], d["box"][1]): d for d in all_tracked}
        for bucket in ("cars", "bikes", "persons", "trucks", "buses",
                       "autorickshaws", "parking_spaces"):
            for det in scene[bucket]:
                key = (det["box"][0], det["box"][1])
                if key in tracked_map:
                    det.update({
                        "track_id":   tracked_map[key].get("track_id", -1),
                        "label":      tracked_map[key].get("label", ""),
                        "trajectory": tracked_map[key].get("trajectory", []),
                    })
                else:
                    det.setdefault("track_id",   -1)
                    det.setdefault("label",       "")
                    det.setdefault("trajectory",  [])
    else:
        for bucket in ("cars", "bikes", "persons", "trucks", "buses",
                       "autorickshaws", "parking_spaces"):
            for det in scene[bucket]:
                det["track_id"]  = -1
                det["label"]     = ""
                det["trajectory"] = []

    # Shared scene analysis (once per frame) — raw image, see Layer 1 note above
    signal_data  = signal_pipeline(raw_img)
    parking_data = parking_pipeline(raw_img)
    sign_data    = traffic_sign_pipeline(raw_img)

    plate_violations:    dict[str, list]  = defaultdict(list)
    vehicle_plate_boxes: dict[str, tuple] = {}
    plate_vehicle_type:  dict[str, str]   = {}
    all_violations: list = []

    # BUGFIX: the dicts above used to be keyed directly by plate_text. Every
    # vehicle with an unreadable plate defaults to the literal string
    # "UNKNOWN" though, and in single-image mode EVERY detection has
    # track_id == -1 (tracking is disabled — see the is_video docstring
    # above), so there was nothing else to tell two different vehicles
    # apart either. A frame with two unrelated bikes that both had
    # unreadable plates (the normal case the UNKNOWN-plate guard exists
    # for) had their violations silently merged into one fused evidence
    # record / one challan, with the evidence crop and track_id coming
    # from whichever vehicle was processed first — a different vehicle's
    # violation could be attributed to it. _vehicle_uid() now gives every
    # detection with an unreadable plate its own bucket key, while still
    # merging by the real plate text when OCR actually succeeds (the
    # original, correct behaviour). vehicle_plate_text maps each bucket
    # key back to the real plate string for display / the UNKNOWN guard.
    vehicle_plate_text: dict[str, str] = {}
    _uid_counter = itertools.count()

    def _vehicle_uid(plate_text: str) -> str:
        if plate_text not in ("UNKNOWN", "", None):
            return plate_text
        return f"UNKNOWN-{next(_uid_counter)}"

    # ── Bikes ─────────────────────────────────────────────────────────────────
    for det in scene["bikes"]:
        tid        = det.get("track_id", -1)
        trajectory = det.get("trajectory", [])
        b_data     = bike_pipeline(raw_img, det["box"])
        scene_conf = det.get("conf", 0.8)

        candidates = evaluate_bike(b_data, signal_data, sign_data, det["box"],
                                   "UNKNOWN", scene_conf, trajectory, tid,
                                   speed_kmh)
        if not candidates:
            continue

        plate_text, _, plate_box = _resolve_plate(raw_img, enhanced_img, det["box"])
        # BUGFIX: previously called evaluate_bike() a second time here,
        # which re-ran confirm_violation() and double-counted the
        # consecutive-frame gate. apply_plate() patches the plate /
        # re-applies the UNKNOWN-plate guard without re-gating.
        candidates = apply_plate(candidates, plate_text)

        key = _vehicle_uid(plate_text)
        all_violations.extend(candidates)
        plate_violations[key].extend(candidates)
        vehicle_plate_boxes.setdefault(key, (det["box"], plate_box))
        plate_vehicle_type.setdefault(key, "bike")
        vehicle_plate_text.setdefault(key, plate_text)

    # ── Cars / Trucks / Buses / Autorickshaws ─────────────────────────────────
    for det in (scene["cars"] + scene.get("trucks", []) +
                scene.get("buses", []) + scene.get("autorickshaws", [])):
        tid        = det.get("track_id", -1)
        trajectory = det.get("trajectory", [])
        scene_conf = det.get("conf", 0.8)

        # Pass the scene-model confidence as a 5th element of the box so
        # car_pipeline's Gate 0 can reject low-confidence detections before
        # running any expert model.  car_pipeline() uses box[:4] for all
        # geometric operations so existing callers are unaffected.
        box_with_conf = det["box"] + [scene_conf]
        c_data     = car_pipeline(raw_img, box_with_conf,
                                   person_boxes=scene["persons"])

        stationary, frames_stat = (
            is_stationary(tid, trajectory) if tid >= 0 else (False, 0)
        )

        candidates = evaluate_car(c_data, signal_data, sign_data, det["box"],
                                  "UNKNOWN", scene_conf, parking_data,
                                  trajectory, frames_stat, tid, speed_kmh)
        if not candidates:
            continue

        plate_text, _, plate_box = _resolve_plate(raw_img, enhanced_img, det["box"])
        candidates = apply_plate(candidates, plate_text)

        key = _vehicle_uid(plate_text)
        all_violations.extend(candidates)
        plate_violations[key].extend(candidates)
        vehicle_plate_boxes.setdefault(key, (det["box"], plate_box))
        plate_vehicle_type.setdefault(key, det.get("label") or "car")
        vehicle_plate_text.setdefault(key, plate_text)

    # ── Pedestrians ──────────────────────────────────────────────────────────
    for det in scene["persons"]:
        tid = det.get("track_id", -1)
        pv  = evaluate_pedestrian(signal_data, det["box"], tid)
        if not pv:
            continue
        # Same fix as bikes/cars above — every pedestrian got bucketed under
        # the single literal key "PEDESTRIAN" before, merging unrelated
        # people's violations into one evidence record.
        key = f"PEDESTRIAN-{next(_uid_counter)}"
        all_violations.extend(pv)
        plate_violations[key].extend(pv)
        vehicle_plate_boxes.setdefault(key, (det["box"], None))
        plate_vehicle_type.setdefault(key, "pedestrian")
        vehicle_plate_text.setdefault(key, "PEDESTRIAN")

    # Layer 4 summary
    summary   = summarize_violations(all_violations)
    annotated = annotate_image(enhanced_img, scene, all_violations, signal_data)
    challans  = []

    # Layer 5 — Evidence + Challan
    for key, violations in plate_violations.items():
        if not violations:
            continue

        plate_text   = vehicle_plate_text.get(key, key)
        fused        = fuse_vehicle_violations(violations, plate_text)
        v_box, p_box = vehicle_plate_boxes.get(key, (None, None))

        # Risk AI (skipped for PEDESTRIAN bucket)
        if plate_text != "PEDESTRIAN":
            risk_score, risk_tier = predict_risk(
                violations,
                speed_kmh=speed_kmh,
                vehicle_type=plate_vehicle_type.get(key, "car"),
            )
            fused["combined_risk"] = risk_score
            fused["top_severity"]  = risk_tier

        record = create_evidence_record(
            plate        = plate_text,
            violations   = violations,
            location     = location,
            camera_id    = camera_id,
            track_id     = violations[0].track_id,
            fused_record = fused,
        )

        image_urls: dict = {}
        if save:
            save_evidence_images(enhanced_img, record, annotated,
                                 vehicle_box=v_box, plate_box=p_box)
            # ── Firebase: upload images to Storage ───────────────────────────
            image_urls = upload_evidence_pack(
                rid          = record["record_id"],
                full_path    = record.get("image_path",   ""),
                vehicle_path = record.get("vehicle_crop", ""),
                plate_path   = record.get("plate_crop",   ""),
            )
            # BUGFIX: image_urls used to only be forwarded to
            # push_to_firestore() below — never merged into `record`, so the
            # local metadata JSON (and therefore generate_challan()'s output
            # and api.py's GET /evidence + GET /challans) never had the
            # Firebase Storage URLs, even after a successful upload.
            record["full_url"]    = image_urls.get("full_url",    "")
            record["vehicle_url"] = image_urls.get("vehicle_url", "")
            record["plate_url"]   = image_urls.get("plate_url",   "")
            write_evidence_metadata(record)

        # BUGFIX: generate_challan() used to unconditionally write a
        # CHN-<uuid>.json file to evidence/challans/ on every call, with no
        # regard for the `save` flag every other persistence call here
        # respects. process_video() calls process_frame(..., save=False, ...)
        # for EVERY sampled frame (every 5th raw frame) and only decides
        # afterwards, via its own 5-second dedup window, which challans
        # should actually be kept. Without this fix, a single continuous
        # 10-second violation sampled at 30fps/5 could write ~60 separate,
        # randomly-uuid'd duplicate challan files to disk before that dedup
        # logic ever got a say — completely flooding evidence/challans/
        # regardless of how clean the in-memory total_challans count looked.
        challan = generate_challan(record, persist=save)

        # ── UNKNOWN-plate guard (④) ──────────────────────────────────────────
        # If plate is unreadable, override review_status to MANUAL_REVIEW so
        # no automatic challan is dispatched — a reviewer must confirm identity.
        if plate_text in ("UNKNOWN", "", None):
            challan["review_status"]    = ReviewStatus.MANUAL_REVIEW
            challan["auto_challan"]     = False
            challan["manual_review_reason"] = "plate_unreadable"
        else:
            # Use the fused batch status from rule_engine
            batch_status = fused.get("review_status", ReviewStatus.MANUAL_REVIEW)
            challan["review_status"] = batch_status
            challan["auto_challan"]  = (batch_status == ReviewStatus.AUTO_APPROVED)

        challans.append(challan)

        # ── Firebase: push challan + violations to Firestore ────────────────
        if save and image_urls is not None:
            push_to_firestore(challan, image_urls)

    return {
        "scene":      scene,
        "violations": [v.to_dict() for v in all_violations],  # ALL violations (AUTO + MANUAL)
        "challans":   challans,   # each challan has review_status field
        "summary":    summary,
        "sign_data":  sign_data,
        # Convenience split so frontend can render both queues separately
        "auto_challans":  [c for c in challans if c.get("auto_challan")],
        "manual_review":  [c for c in challans if not c.get("auto_challan")],
    }


# ── Video pipeline ─────────────────────────────────────────────────────────────

def process_video(video_path: str,
                  camera_id:      str   = "CAM-01",
                  location:       str   = "Unknown",
                  save:           bool  = True,
                  display:        bool  = False,
                  road_direction: tuple = (1, 0)) -> dict:
    """
    Frame-by-frame processing with DeepSORT tracking.
    Deduplicates challans so the same violation is not re-issued within ~5 s.
    Calls reset_confirmation_state() at start so frame counters are clean.
    """
    # Clear consecutive-frame counters from any previous run
    reset_confirmation_state()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open: {video_path}")

    fps         = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = total_violations = total_challans = 0
    issued:          dict[str, int]   = {}
    DEDUP_FRAMES     = int(fps * 5)

    PIXEL_TO_METER   = 0.05
    _prev_positions: dict[int, tuple] = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        if frame_count % 5 != 0:
            continue

        scene_raw  = detect_scene(frame)
        all_tracks = update_tracks(scene_raw["all"], frame)

        speeds: list[float] = []
        for t in all_tracks:
            tid = t.get("track_id", -1)
            if tid < 0:
                continue
            cx = (t["box"][0] + t["box"][2]) // 2
            cy = (t["box"][1] + t["box"][3]) // 2
            if tid in _prev_positions:
                px, py, pf    = _prev_positions[tid]
                frames_elapsed = frame_count - pf
                if frames_elapsed > 0:
                    dist_m = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5 * PIXEL_TO_METER
                    time_s = frames_elapsed / fps
                    speeds.append(min((dist_m / time_s) * 3.6, 200.0))
            _prev_positions[tid] = (cx, cy, frame_count)

        avg_speed = float(sum(speeds) / len(speeds)) if speeds else 0.0

        result = process_frame(frame, camera_id, location, save=False,
                               road_direction=road_direction,
                               speed_kmh=avg_speed,
                               is_video=True)

        for challan in result["challans"]:
            # Only deduplicate and count auto-approved challans toward totals;
            # manual-review ones are queued separately (not deduplicated).
            key  = (f"{challan.get('plate_number','?')}-"
                    f"{challan['violations'][0]['violation_type']}")
            last = issued.get(key, -DEDUP_FRAMES - 1)
            if frame_count - last > DEDUP_FRAMES:
                issued[key] = frame_count
                if save:
                    vid_record = {
                        "record_id":     challan["challan_id"].replace("CHN-", ""),
                        "timestamp":     challan["issued_at"],
                        "camera_id":     camera_id,
                        "location":      location,
                        "plate_number":  challan.get("plate_number", "UNKNOWN"),
                        "violations":    challan["violations"],
                        "total_fine":    challan["total_fine_inr"],
                        "combined_risk": challan.get("combined_risk", 50),
                        "top_severity":  challan.get("top_severity", "Medium"),
                        "review_status": challan.get("review_status",
                                                      ReviewStatus.MANUAL_REVIEW),
                    }
                    save_evidence_images(frame, vid_record)
                    # ── Firebase ─────────────────────────────────────────────
                    vid_urls = upload_evidence_pack(
                        rid       = vid_record["record_id"],
                        full_path = vid_record.get("image_path", ""),
                    )
                    # BUGFIX: same fix as the image pipeline above — merge the
                    # Storage URLs into the record before writing metadata,
                    # instead of only handing them to Firestore.
                    vid_record["full_url"] = vid_urls.get("full_url", "")
                    write_evidence_metadata(vid_record)
                    push_to_firestore(challan, vid_urls)
                total_challans += 1

        total_violations += result["summary"]["total_violations"]

        if display:
            ann = annotate_image(
                frame, result["scene"], [], signal_pipeline(frame))
            cv2.imshow("HMATES", ann)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    if display:
        cv2.destroyAllWindows()

    print(f"\n[Video Done]  frames:{frame_count}  "
          f"violations:{total_violations}  challans:{total_challans}")
    return {"frames": frame_count,
            "violations": total_violations,
            "challans": total_challans}


# ── Demo ───────────────────────────────────────────────────────────────────────

def run_demo() -> None:
    reset_confirmation_state()
    print("\n[DEMO] Running full pipeline on synthetic image …")
    img = np.full((720, 1280, 3), 80, dtype=np.uint8)
    cv2.putText(img, "HMATES v2 — DEMO MODE  (no model files needed)",
                (120, 360), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 3)
    result = process_frame(img, "DEMO-CAM", "Demo Location", save=False)
    print(f"[DEMO] Pipeline OK — violations:{result['summary']['total_violations']}")
    print(f"[DEMO] Review breakdown: {result['summary'].get('review_breakdown', {})}")
    signs = result.get("sign_data", {})
    print(f"[DEMO] Active signs detected: {signs.get('active_signs', set())}")
    print("[DEMO] All modules functional.")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="HMATES v2 — Hierarchical Multi-Agent Traffic Enforcement"
    )
    ap.add_argument("--image",     type=str,  help="Path to input image")
    ap.add_argument("--video",     type=str,  help="Path to input video")
    ap.add_argument("--camera",    type=str,  default="CAM-01")
    ap.add_argument("--location",  type=str,  default="Unknown")
    ap.add_argument("--display",   action="store_true")
    ap.add_argument("--no-save",   action="store_true")
    ap.add_argument("--report",    action="store_true")
    ap.add_argument("--demo",      action="store_true")
    ap.add_argument("--dashboard", action="store_true")
    ap.add_argument("--speed",     type=float, default=0.0,
                    help="Override vehicle speed (km/h) for image mode")
    args = ap.parse_args()

    if args.demo:
        run_demo(); return

    if args.report:
        r = generate_summary_report()
        print_report(r)
        save_report()
        return

    if args.dashboard:
        import subprocess
        subprocess.run([sys.executable, "-m", "streamlit", "run", "dashboard.py"])
        return

    if args.video:
        process_video(args.video, args.camera, args.location,
                      save=not args.no_save, display=args.display)
        return

    if args.image:
        if not Path(args.image).exists():
            print(f"[ERROR] File not found: {args.image}")
            sys.exit(1)
        raw    = load_image(args.image)
        result = process_frame(raw, args.camera, args.location,
                               save=not args.no_save,
                               speed_kmh=args.speed)
        print(f"\nSummary: {result['summary']}")
        challans = result.get("challans", [])
        auto     = result.get("auto_challans", [c for c in challans if c.get("auto_challan")])
        review   = result.get("manual_review",  [c for c in challans if not c.get("auto_challan")])
        print(f"Auto-challans: {len(auto)}   Manual-review queue: {len(review)}")
        violations = result.get("violations", [])
        print(f"Total violations detected: {len(violations)}")
        for v in violations:
            print(f"  [{v.get('review_status','?')}] {v.get('violation_type','?')} "
                  f"conf={v.get('confidence',0):.2f} plate={v.get('plate_number','?')}")
        signs = result.get("sign_data", {})
        if signs.get("active_signs"):
            print(f"Signs detected: {signs['active_signs']}")
        return

    print("[ERROR] Provide --image, --video, --report, --demo, or --dashboard")
    sys.exit(1)


if __name__ == "__main__":
    main()