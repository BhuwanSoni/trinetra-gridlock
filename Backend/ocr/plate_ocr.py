"""
plate_ocr.py  (Improved — PaddleOCR primary, EasyOCR fallback)
──────────────────────────────────────────────────────────────
License Plate Recognition for Indian number plates.

Priority:
  1. PaddleOCR  (85-95% accuracy, recommended)
  2. EasyOCR    (70-85% accuracy, automatic fallback)

Install best option:
  pip install paddlepaddle paddleocr   # GPU build optional
  pip install easyocr                  # fallback

Plate detection is handled by the YOLO plate model in detector.py.
This module receives the cropped plate image and returns clean text.
"""

import re
import cv2
import numpy as np

# ── Reader instances (loaded lazily — each ~200-400 MB) ──────────────────────

_paddle_reader = None
_easy_reader   = None


def _get_paddle():
    global _paddle_reader
    if _paddle_reader is None:
        try:
            from paddleocr import PaddleOCR
            _paddle_reader = PaddleOCR(lang="en")
            print("[OCR] PaddleOCR loaded (primary).")
        except ImportError:
            print("[WARN] paddleocr not installed — falling back to EasyOCR.")
            print("       pip install paddlepaddle paddleocr")
    return _paddle_reader


def _get_easy():
    global _easy_reader
    if _easy_reader is None:
        try:
            import easyocr
            _easy_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
            print("[OCR] EasyOCR loaded (fallback).")
        except ImportError:
            print("[WARN] easyocr not installed either. pip install easyocr")
    return _easy_reader


# ── Plate preprocessing ───────────────────────────────────────────────────────

def preprocess_plate(plate_img: np.ndarray) -> np.ndarray:
    """
    Enhance a cropped plate image for better OCR accuracy.
    Steps: upscale → greyscale → bilateral filter → adaptive threshold
    """
    if plate_img is None or plate_img.size == 0:
        return plate_img

    h, w = plate_img.shape[:2]
    if w < 100:
        scale = 100 / w
        plate_img = cv2.resize(plate_img,
                               (int(w * scale), int(h * scale)),
                               interpolation=cv2.INTER_CUBIC)

    gray     = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
    filtered = cv2.bilateralFilter(gray, 11, 17, 17)
    thresh   = cv2.adaptiveThreshold(
        filtered, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2,
    )
    # Return 3-channel for PaddleOCR compatibility
    return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)


# ── PaddleOCR reader ──────────────────────────────────────────────────────────

def _read_paddle(plate_img: np.ndarray) -> tuple[str, float]:
    """
    Run PaddleOCR on a preprocessed plate crop.
    Returns (text, confidence).
    """
    reader = _get_paddle()
    if reader is None:
        return "", 0.0

    try:
        result = reader.ocr(plate_img, cls=True)
        if not result or not result[0]:
            return "", 0.0

        # result[0] is a list of [box, (text, conf)] per text region
        best_text  = ""
        best_conf  = 0.0
        for line in result[0]:
            text, conf = line[1]
            if conf > best_conf:
                best_conf = conf
                best_text = text
        return best_text, best_conf

    except Exception as e:
        print(f"[PaddleOCR ERROR] {e}")
        return "", 0.0


# ── EasyOCR reader (fallback) ─────────────────────────────────────────────────

def _read_easy(plate_img: np.ndarray) -> tuple[str, float]:
    """
    Run EasyOCR on a preprocessed plate crop.
    Returns (text, confidence).
    """
    reader = _get_easy()
    if reader is None:
        return "", 0.0

    # EasyOCR wants greyscale or BGR; convert from our 3-ch preprocessed
    gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
    try:
        results = reader.readtext(gray, detail=1)
        if not results:
            return "", 0.0
        best = max(results, key=lambda r: r[2])
        return best[1], best[2]
    except Exception as e:
        print(f"[EasyOCR ERROR] {e}")
        return "", 0.0


# ── Public read_plate ─────────────────────────────────────────────────────────

def read_plate(plate_crop: np.ndarray) -> str:
    """
    Run the best available OCR engine on a cropped plate image.
    Returns cleaned plate text, or "UNKNOWN" on failure.
    """
    processed = preprocess_plate(plate_crop)

    # Try PaddleOCR first (higher accuracy)
    text, conf = _read_paddle(processed)

    # Fall back to EasyOCR if Paddle unavailable or low confidence
    if not text or conf < 0.3:
        text_e, conf_e = _read_easy(processed)
        if conf_e > conf:
            text, conf = text_e, conf_e

    if conf < 0.3 or not text:
        return "UNKNOWN"

    return clean_plate_text(text)


def read_plate_all(plate_crop: np.ndarray) -> list:
    """Return all OCR results as (text, confidence) tuples (best engine only)."""
    processed = preprocess_plate(plate_crop)

    # Try Paddle
    reader = _get_paddle()
    if reader:
        try:
            result = reader.ocr(processed, cls=True)
            if result and result[0]:
                return [(line[1][0], round(line[1][1], 3)) for line in result[0]]
        except Exception:
            pass

    # Fallback EasyOCR
    gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
    er = _get_easy()
    if er:
        try:
            return [(r[1], round(r[2], 3)) for r in er.readtext(gray, detail=1)]
        except Exception:
            pass

    return []


# ── Text cleaning ─────────────────────────────────────────────────────────────

_CHAR_MAP = {"O": "0", "I": "1", "S": "5", "Z": "2", "B": "8", "G": "6"}

# Indian plate: XX 00 XX 0000  (loose match)
_INDIA_PLATE_RE = re.compile(
    r"^[A-Z]{2}\s?\d{1,2}\s?[A-Z]{1,3}\s?\d{1,4}$"
)


def clean_plate_text(text: str) -> str:
    """
    Normalise OCR output:
    • Uppercase → strip non-alphanumeric → collapse spaces
    • Correct common OCR letter→digit errors in digit positions
    """
    text = text.upper().strip()
    text = re.sub(r"[^A-Z0-9 ]", "", text)
    text = re.sub(r"\s+", " ", text)

    # Positional correction for Indian plates (positions 2-3 are digits)
    corrected = []
    for i, ch in enumerate(text.replace(" ", "")):
        if i in (2, 3) and ch in _CHAR_MAP:
            corrected.append(_CHAR_MAP[ch])
        else:
            corrected.append(ch)
    text = "".join(corrected)
    return text if text else "UNKNOWN"


def is_valid_plate(text: str) -> bool:
    """Loosely validate against Indian motor vehicle plate format."""
    return bool(_INDIA_PLATE_RE.match(text.replace(" ", "")))


# ── Combined crop + read ──────────────────────────────────────────────────────

def extract_plate_from_image(img: np.ndarray,
                              plate_detections: list) -> dict:
    """
    Given an image and YOLO plate detection dicts, crop the best plate
    and run OCR.

    Returns:
        {"plate_text": str, "confidence": float, "box": list | None}
    """
    if not plate_detections:
        return {"plate_text": "UNKNOWN", "confidence": 0.0, "box": None}

    best = max(plate_detections, key=lambda d: d["conf"])
    x1, y1, x2, y2 = best["box"]
    h, w = img.shape[:2]
    crop = img[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]

    if crop.size == 0:
        return {"plate_text": "UNKNOWN", "confidence": 0.0, "box": best["box"]}

    plate_text = read_plate(crop)
    return {
        "plate_text": plate_text,
        "confidence": round(best["conf"], 3),
        "box":        best["box"],
    }