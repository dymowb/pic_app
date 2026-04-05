"""
Image quality metrics — pure Python / NumPy / OpenCV, no Qt dependency.

Metrics
-------
sharpness   — Laplacian variance (higher = sharper)
exposure    — 0–100 score penalising under/over-exposure and clipping
noise       — 0–100 score (100 = very clean, 0 = very noisy)
resolution  — total pixel count (width × height)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


@dataclass
class ImageMetrics:
    sharpness: float    # Laplacian variance; higher = sharper (unbounded above 0)
    exposure: float     # 0–100; 100 = perfectly exposed
    noise: float        # 0–100; 100 = clean, 0 = very noisy
    resolution: int     # total pixels (width × height)
    width: int
    height: int


def compute_metrics(path: Path) -> ImageMetrics:
    """
    Compute all quality metrics for a single image.

    Raises OSError / PIL exceptions if the file cannot be opened.
    """
    with Image.open(path) as img:
        img_rgb = img.convert("RGB")
        width, height = img_rgb.size

    arr = np.array(img_rgb, dtype=np.uint8)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    return ImageMetrics(
        sharpness=_sharpness(gray),
        exposure=_exposure(gray),
        noise=_noise(gray),
        resolution=width * height,
        width=width,
        height=height,
    )


# ---------------------------------------------------------------------------
# Individual metric functions (also exported for tests)
# ---------------------------------------------------------------------------

def sharpness(gray: np.ndarray) -> float:
    """
    Laplacian variance — measures edge strength.
    A sharp image has high-contrast edges → high variance.
    """
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return float(lap.var())


def exposure(gray: np.ndarray) -> float:
    """
    Exposure quality score (0–100).

    Penalises:
    - Deviation of mean brightness from the ideal midpoint (128)
    - Clipping: fraction of pixels at absolute black (≤5) or white (≥250)
    """
    mean = float(gray.mean())
    total = gray.size

    # Mean deviation penalty (0–1, lower = worse)
    mean_score = 1.0 - abs(mean - 128.0) / 128.0

    # Clipping penalty
    clip_black = float(np.sum(gray <= 5)) / total
    clip_white = float(np.sum(gray >= 250)) / total
    clip_penalty = clip_black + clip_white
    clip_score = max(0.0, 1.0 - clip_penalty * 4)  # ×4 so 25% clipping = 0

    return round((0.6 * mean_score + 0.4 * clip_score) * 100, 2)


def noise(gray: np.ndarray) -> float:
    """
    Noise estimate score (0–100, 100 = very clean).

    Uses the high-frequency residual: original minus Gaussian blur.
    The RMS of this residual estimates the noise floor.
    Lower RMS → cleaner image → higher score.
    """
    blurred = cv2.GaussianBlur(gray.astype(np.float32), (5, 5), 0)
    residual = gray.astype(np.float32) - blurred
    rms = float(np.sqrt(np.mean(residual ** 2)))

    # Empirical scale: rms~0 → score 100, rms~20+ → score ~0
    score = max(0.0, 100.0 - rms * 5)
    return round(score, 2)


def _sharpness(gray: np.ndarray) -> float:
    return sharpness(gray)

def _exposure(gray: np.ndarray) -> float:
    return exposure(gray)

def _noise(gray: np.ndarray) -> float:
    return noise(gray)
