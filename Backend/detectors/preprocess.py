"""
preprocess.py
Image enhancement and preprocessing pipeline for traffic images.
Handles low light, rain, shadows, motion blur, and normalization.
"""

import cv2
import numpy as np
from pathlib import Path


def enhance_image(img_path: str) -> np.ndarray:
    """
    Full preprocessing pipeline for a traffic image file.
    Returns enhanced BGR numpy array.
    """
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"Could not load image: {img_path}")
    return enhance_array(img)


def enhance_array(img: np.ndarray) -> np.ndarray:
    """
    Full preprocessing pipeline for an in-memory BGR numpy array.
    Steps: CLAHE → denoise → sharpen → normalize
    """
    img = apply_clahe(img)
    img = denoise(img)
    img = sharpen(img)
    img = normalize_brightness(img)
    return img


# ─── Individual Enhancement Steps ────────────────────────────────────────────

def apply_clahe(img: np.ndarray, clip_limit: float = 3.0,
                tile_grid: tuple = (8, 8)) -> np.ndarray:
    """
    Contrast Limited Adaptive Histogram Equalization.
    Works in LAB color space to avoid color distortion.
    Helps with low-light and shadowed images.
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
    l = clahe.apply(l)

    enhanced = cv2.merge((l, a, b))
    return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)


def denoise(img: np.ndarray, h: int = 10) -> np.ndarray:
    """
    Fast Gaussian denoise for real-time performance on CPU.
    Replaces fastNlMeansDenoisingColored (~4500ms) with GaussianBlur (~2ms).
    Sufficient for traffic CCTV footage where noise is mild.
    For high-noise / rainy footage, set env var HMATES_SLOW_DENOISE=1
    to re-enable NLM denoising at the cost of speed.
    """
    import os
    if os.environ.get("HMATES_SLOW_DENOISE") == "1":
        return cv2.fastNlMeansDenoisingColored(img, None, h, h, 7, 21)
    return cv2.GaussianBlur(img, (3, 3), 0)


def sharpen(img: np.ndarray) -> np.ndarray:
    """
    Unsharp masking to recover detail lost in motion blur or compression.
    """
    gaussian = cv2.GaussianBlur(img, (0, 0), 3)
    return cv2.addWeighted(img, 1.5, gaussian, -0.5, 0)


def normalize_brightness(img: np.ndarray) -> np.ndarray:
    """
    Normalize overall brightness into a safe range.
    Prevents overexposed or underexposed frames from skewing detections.
    """
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    v = cv2.normalize(v, None, 0, 255, cv2.NORM_MINMAX)
    return cv2.cvtColor(cv2.merge((h, s, v)), cv2.COLOR_HSV2BGR)


def resize_for_model(img: np.ndarray, size: int = 640) -> np.ndarray:
    """
    Resize image to standard YOLO input size while preserving aspect ratio.
    Pads with grey to fill the square.
    """
    h, w = img.shape[:2]
    scale = size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h))

    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    pad_top = (size - new_h) // 2
    pad_left = (size - new_w) // 2
    canvas[pad_top:pad_top + new_h, pad_left:pad_left + new_w] = resized
    return canvas


def crop_roi(img: np.ndarray, box: list) -> np.ndarray:
    """
    Crop a region of interest from the image using [x1, y1, x2, y2] box.
    Clamps coordinates to image boundaries.
    """
    h, w = img.shape[:2]
    x1, y1, x2, y2 = box
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(w, x2)
    y2 = min(h, y2)
    return img[y1:y2, x1:x2]


def load_image(source) -> np.ndarray:
    """
    Flexible loader: accepts a file path (str/Path) or a numpy array.
    Always returns a BGR numpy array.
    """
    if isinstance(source, (str, Path)):
        img = cv2.imread(str(source))
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {source}")
        return img
    elif isinstance(source, np.ndarray):
        return source.copy()
    else:
        raise TypeError(f"Unsupported image type: {type(source)}")