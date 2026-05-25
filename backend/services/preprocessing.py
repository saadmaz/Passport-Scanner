"""Image preprocessing pipeline for passport MRZ extraction."""

from __future__ import annotations

import io
from typing import List, Tuple

import cv2
import numpy as np
from PIL import Image, ExifTags, UnidentifiedImageError

MAX_FILE_BYTES = 10 * 1024 * 1024   # 10 MB
MAX_PIXELS = 50_000_000              # 50 MP hard guard
TARGET_LONG_EDGE = 1600              # upscale target for Tesseract accuracy
MRZ_CROP_FRACTIONS = [0.22, 0.28, 0.35, 0.42]  # multiple crops to try


class ImageTooLargeError(ValueError):
    pass


class UnsupportedFormatError(ValueError):
    pass


def _fix_exif_orientation(img: Image.Image) -> Image.Image:
    try:
        exif = img._getexif()  # type: ignore[attr-defined]
        if not exif:
            return img
        orient_tag = next(
            (k for k, v in ExifTags.TAGS.items() if v == "Orientation"), None
        )
        if orient_tag and orient_tag in exif:
            orientation = exif[orient_tag]
            rotations = {3: 180, 6: 270, 8: 90}
            if orientation in rotations:
                img = img.rotate(rotations[orientation], expand=True)
    except Exception:
        pass
    return img


def _upscale_if_small(gray: np.ndarray) -> np.ndarray:
    h, w = gray.shape[:2]
    long_edge = max(h, w)
    if long_edge >= TARGET_LONG_EDGE:
        return gray
    scale = TARGET_LONG_EDGE / long_edge
    new_w, new_h = int(w * scale), int(h * scale)
    return cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Correct skew up to ±15 degrees."""
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
    if lines is None:
        return gray
    angles = []
    for rho, theta in lines[:, 0]:
        angle = (theta * 180 / np.pi) - 90
        if abs(angle) <= 15.0:
            angles.append(angle)
    if not angles:
        return gray
    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5:
        return gray
    h, w = gray.shape
    center = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _enhance_variants(gray: np.ndarray) -> List[np.ndarray]:
    """Return multiple binarized variants of the image for OCR to try."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    results: List[np.ndarray] = []

    # Variant 1: CLAHE + Gaussian blur + Otsu (good for clean images)
    blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results.append(otsu)

    # Variant 2: CLAHE + adaptive threshold (good for uneven lighting)
    adaptive = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )
    results.append(adaptive)

    return results


def _crop_mrz_candidates(binary: np.ndarray) -> List[np.ndarray]:
    """Return MRZ region crops at multiple heights plus a morphology-detected region."""
    h, w = binary.shape
    candidates: List[np.ndarray] = []

    # Try morphological detection: look for wide horizontal text bands in lower image
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(1, int(w * 0.05)), 1))
    dilated = cv2.dilate(255 - binary, kernel, iterations=3)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mrz_rows: List[Tuple[int, int]] = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if cw > w * 0.55 and y > h * 0.45:
            mrz_rows.append((y, y + ch))
    if mrz_rows:
        y1 = max(0, min(r[0] for r in mrz_rows) - 5)
        y2 = min(h, max(r[1] for r in mrz_rows) + 5)
        if y2 - y1 > 10:
            candidates.append(binary[y1:y2, :])

    # Fixed-percentage crops
    for frac in MRZ_CROP_FRACTIONS:
        mrz_h = int(h * frac)
        candidates.append(binary[-mrz_h:, :])

    return candidates


def preprocess(image_bytes: bytes, content_type: str) -> Tuple[bytes, List[np.ndarray]]:
    """Full pipeline: validate → orient → upscale → enhance → MRZ candidates.

    Returns:
        (jpeg_bytes_of_full_image, list_of_mrz_region_arrays)
    """
    if len(image_bytes) > MAX_FILE_BYTES:
        raise ImageTooLargeError(f"Image exceeds {MAX_FILE_BYTES // 1_048_576} MB limit")

    allowed = {"image/jpeg", "image/jpg", "image/png"}
    if content_type.lower() not in allowed:
        raise UnsupportedFormatError(f"Unsupported format: {content_type}")

    try:
        pil_img = Image.open(io.BytesIO(image_bytes))
    except UnidentifiedImageError as exc:
        raise UnsupportedFormatError("Cannot decode image") from exc

    w, h = pil_img.size
    if w * h > MAX_PIXELS:
        raise ImageTooLargeError(f"Image exceeds {MAX_PIXELS // 1_000_000} MP limit")

    pil_img = _fix_exif_orientation(pil_img)
    pil_img = pil_img.convert("RGB")

    arr = np.array(pil_img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # Upscale small images so Tesseract has enough resolution
    gray = _upscale_if_small(gray)
    gray = _deskew(gray)

    # Build all candidate MRZ regions across all enhancement variants
    mrz_candidates: List[np.ndarray] = []
    for enhanced in _enhance_variants(gray):
        mrz_candidates.extend(_crop_mrz_candidates(enhanced))

    # Re-encode original (un-upscaled) image as JPEG
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=92)
    return buf.getvalue(), mrz_candidates
