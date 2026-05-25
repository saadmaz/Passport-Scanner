"""Preprocessing pipeline tests."""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image

from backend.services.preprocessing import (
    MAX_FILE_BYTES,
    MIN_LONG_EDGE,
    ImageTooLargeError,
    ImageTooSmallError,
    UnsupportedFormatError,
    preprocess,
)


def _make_jpeg(width: int, height: int) -> bytes:
    img = Image.new("RGB", (width, height), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_png(width: int, height: int) -> bytes:
    img = Image.new("RGB", (width, height), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestPreprocess:
    def test_valid_jpeg_returns_bytes_and_array(self):
        data = _make_jpeg(1600, 1200)
        jpeg_out, mrz = preprocess(data, "image/jpeg")
        assert isinstance(jpeg_out, bytes)
        assert len(jpeg_out) > 0
        assert isinstance(mrz, np.ndarray)
        assert mrz.ndim == 2  # grayscale

    def test_valid_png_accepted(self):
        data = _make_png(1600, 1200)
        jpeg_out, mrz = preprocess(data, "image/png")
        assert isinstance(jpeg_out, bytes)

    def test_file_too_large_raises(self):
        oversized = b"X" * (MAX_FILE_BYTES + 1)
        with pytest.raises(ImageTooLargeError):
            preprocess(oversized, "image/jpeg")

    def test_image_too_small_raises(self):
        data = _make_jpeg(600, 400)
        with pytest.raises(ImageTooSmallError):
            preprocess(data, "image/jpeg")

    def test_unsupported_format_raises(self):
        data = _make_jpeg(1600, 1200)
        with pytest.raises(UnsupportedFormatError):
            preprocess(data, "image/gif")

    def test_mrz_region_height(self):
        data = _make_jpeg(1600, 1200)
        _, mrz = preprocess(data, "image/jpeg")
        # MRZ region should be roughly 22% of image height
        expected_h = int(1200 * 0.22)
        assert abs(mrz.shape[0] - expected_h) <= 2

    def test_invalid_image_bytes_raises(self):
        with pytest.raises(UnsupportedFormatError):
            preprocess(b"not an image at all", "image/jpeg")
