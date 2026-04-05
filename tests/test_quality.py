"""Tests for analysis.quality — per-image quality metrics."""

import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

SRC = Path(__file__).parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import cv2
from analysis.quality import (
    ImageMetrics,
    compute_metrics,
    sharpness,
    exposure,
    noise,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gray(arr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_RGB2GRAY)


def _solid(color=(128, 128, 128), size=(200, 200)) -> np.ndarray:
    arr = np.full((*size, 3), color, dtype=np.uint8)
    return arr


def _checkerboard(size=200, square=10) -> np.ndarray:
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    for y in range(0, size, square):
        for x in range(0, size, square):
            if (x // square + y // square) % 2 == 0:
                arr[y:y+square, x:x+square] = 255
    return arr


def _save(arr: np.ndarray, path: Path) -> Path:
    Image.fromarray(arr).save(path)
    return path


# ---------------------------------------------------------------------------
# Sharpness
# ---------------------------------------------------------------------------

def test_sharpness_sharp_image_higher_than_blurry():
    """A crisp checkerboard must score higher than a blurred version."""
    sharp_arr = _checkerboard()
    sharp_gray = _gray(sharp_arr)

    blurry_gray = cv2.GaussianBlur(sharp_gray, (21, 21), 0)

    assert sharpness(sharp_gray) > sharpness(blurry_gray)


def test_sharpness_returns_non_negative():
    arr = _solid()
    assert sharpness(_gray(arr)) >= 0


def test_sharpness_uniform_image_is_near_zero():
    """A flat uniform image has no edges — Laplacian variance is ~0."""
    arr = _solid((100, 100, 100))
    score = sharpness(_gray(arr))
    assert score < 5.0


# ---------------------------------------------------------------------------
# Exposure
# ---------------------------------------------------------------------------

def test_exposure_mid_grey_scores_high():
    """A mid-grey image (mean ≈ 128) should score near 100."""
    arr = _solid((128, 128, 128))
    score = exposure(_gray(arr))
    assert score >= 55.0


def test_exposure_pure_black_scores_low():
    arr = _solid((0, 0, 0))
    score = exposure(_gray(arr))
    assert score < 50.0


def test_exposure_pure_white_scores_low():
    arr = _solid((255, 255, 255))
    score = exposure(_gray(arr))
    assert score < 50.0


def test_exposure_in_range():
    """Exposure score must always be in [0, 100]."""
    for color in [(0, 0, 0), (128, 128, 128), (255, 255, 255), (60, 120, 180)]:
        arr = _solid(color)
        s = exposure(_gray(arr))
        assert 0.0 <= s <= 100.0


# ---------------------------------------------------------------------------
# Noise
# ---------------------------------------------------------------------------

def test_noise_clean_image_scores_high():
    """A smooth gradient image has low noise → high score."""
    arr = np.zeros((200, 200, 3), dtype=np.uint8)
    for i in range(200):
        arr[:, i] = i  # horizontal gradient
    score = noise(_gray(arr))
    assert score >= 60.0


def test_noise_noisy_image_scores_lower_than_clean():
    rng = np.random.default_rng(42)
    clean = np.full((200, 200, 3), 128, dtype=np.uint8)
    noisy = np.clip(clean.astype(int) + rng.integers(-50, 50, clean.shape), 0, 255).astype(np.uint8)

    score_clean = noise(_gray(clean))
    score_noisy = noise(_gray(noisy))
    assert score_clean > score_noisy


def test_noise_in_range():
    arr = _solid((128, 128, 128))
    s = noise(_gray(arr))
    assert 0.0 <= s <= 100.0


# ---------------------------------------------------------------------------
# compute_metrics (integration)
# ---------------------------------------------------------------------------

def test_compute_metrics_returns_dataclass(tmp_path):
    path = _save(_solid((128, 128, 128)), tmp_path / "img.png")
    m = compute_metrics(path)
    assert isinstance(m, ImageMetrics)


def test_compute_metrics_resolution(tmp_path):
    arr = np.zeros((150, 200, 3), dtype=np.uint8)
    path = _save(arr, tmp_path / "img.png")
    m = compute_metrics(path)
    assert m.width == 200
    assert m.height == 150
    assert m.resolution == 200 * 150


def test_compute_metrics_all_scores_in_range(tmp_path):
    path = _save(_checkerboard(), tmp_path / "checker.png")
    m = compute_metrics(path)
    assert m.sharpness >= 0
    assert 0 <= m.exposure <= 100
    assert 0 <= m.noise <= 100


def test_compute_metrics_raises_on_missing_file(tmp_path):
    with pytest.raises(Exception):
        compute_metrics(tmp_path / "ghost.jpg")
