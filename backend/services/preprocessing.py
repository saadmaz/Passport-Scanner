"""Image preprocessing pipeline for passport MRZ extraction."""

from __future__ import annotations

import io
import math
from typing import Tuple

import cv2
import numpy as np
from PIL import Image, ExifTags, UnidentifiedImageError

MAX_FILE_BYTES = 10 * 1024 * 1024       # 10 MB
MAX_PIXELS = 50_000_000                  # 50 MP hard guard
MIN_LONG_EDGE = 1400                     # minimum resolution (px)
DESKEW_LIMIT_DEG = 15.0


class ImageTooLargeError(ValueError):
    pass


class ImageTooSmallError(ValueError):
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


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Correct skew up to ±DESKEW_LIMIT_DEG degrees."""
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
    if lines is None:
        return gray
    angles = []
    for rho, theta in lines[:, 0]:
        angle = (theta * 180 / np.pi) - 90
        if abs(angle) <= DESKEW_LIMIT_DEG:
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


def preprocess(image_bytes: bytes, content_type: str) -> Tuple[bytes, np.ndarray]:
    """Full pipeline: validate → orient → grayscale → enhance → crop MRZ → deskew.

    Returns:
        (jpeg_bytes_of_full_image, mrz_region_ndarray)
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

    # Pixel bomb guard
    w, h = pil_img.size
    if w * h > MAX_PIXELS:
        raise ImageTooLargeError(f"Image exceeds {MAX_PIXELS // 1_000_000} MP limit")

    # Resolution check
    if max(w, h) < MIN_LONG_EDGE:
        raise ImageTooSmallError(
            f"Image long edge {max(w,h)}px is below minimum {MIN_LONG_EDGE}px"
        )

    pil_img = _fix_exif_orientation(pil_img)
    pil_img = pil_img.convert("RGB")

    # Convert to OpenCV
    arr = np.array(pil_img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # Contrast normalization + binarization
    gray = cv2.equalizeHist(gray)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # MRZ region: bottom 22% of image
    mrz_h = int(binary.shape[0] * 0.22)
    mrz_region = binary[-mrz_h:, :]

    mrz_region = _deskew(mrz_region)

    # Re-encode full image as JPEG for Claude Vision
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=92)
    return buf.getvalue(), mrz_region
