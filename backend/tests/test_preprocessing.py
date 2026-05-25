"""Preprocessing pipeline tests."""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image

from backend.services.preprocessing import (
    MAX_FILE_BYTES,
    ImageTooLargeError,
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
    def test_valid_jpeg_returns_bytes_and_candidates(self):
        data = _make_jpeg(1600, 1200)
        jpeg_out, mrz_candidates = preprocess(data, "image/jpeg")
        assert isinstance(jpeg_out, bytes)
        assert len(jpeg_out) > 0
        assert isinstance(mrz_candidates, list)
        assert len(mrz_candidates) > 0
        assert all(isinstance(c, np.ndarray) for c in mrz_candidates)

    def test_valid_png_accepted(self):
        data = _make_png(1600, 1200)
        jpeg_out, mrz_candidates = preprocess(data, "image/png")
        assert isinstance(jpeg_out, bytes)
        assert len(mrz_candidates) > 0

    def test_small_image_accepted(self):
        data = _make_jpeg(600, 400)
        jpeg_out, mrz_candidates = preprocess(data, "image/jpeg")
        assert isinstance(jpeg_out, bytes)

    def test_file_too_large_raises(self):
        oversized = b"X" * (MAX_FILE_BYTES + 1)
        with pytest.raises(ImageTooLargeError):
            preprocess(oversized, "image/jpeg")

    def test_unsupported_format_raises(self):
        data = _make_jpeg(1600, 1200)
        with pytest.raises(UnsupportedFormatError):
            preprocess(data, "image/gif")

    def test_mrz_candidates_are_grayscale(self):
        data = _make_jpeg(1600, 1200)
        _, mrz_candidates = preprocess(data, "image/jpeg")
        for candidate in mrz_candidates:
            assert candidate.ndim == 2

    def test_invalid_image_bytes_raises(self):
        with pytest.raises(UnsupportedFormatError):
            preprocess(b"not an image at all", "image/jpeg")
