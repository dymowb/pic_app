"""Tests for analysis.scorer — weighted scoring and recommendation."""

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from analysis.quality import ImageMetrics
from analysis.scorer import ScoringWeights, ImageScore, score_group


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _metrics(sharpness=100.0, exposure=80.0, noise=90.0, resolution=4_000_000,
             width=2000, height=2000) -> ImageMetrics:
    return ImageMetrics(
        sharpness=sharpness, exposure=exposure, noise=noise,
        resolution=resolution, width=width, height=height,
    )


def _paths(n: int) -> list[Path]:
    return [Path(f"/fake/img_{i}.jpg") for i in range(n)]


# ---------------------------------------------------------------------------
# ScoringWeights
# ---------------------------------------------------------------------------

def test_weights_default_sum_to_one():
    w = ScoringWeights()
    assert abs(w.sharpness + w.exposure + w.resolution - 1.0) < 0.001


def test_weights_from_percent():
    w = ScoringWeights.from_percent(sharpness=60, exposure=30, resolution=10)
    assert abs(w.sharpness - 0.60) < 0.001
    assert abs(w.exposure - 0.30) < 0.001


def test_weights_invalid_sum_raises():
    with pytest.raises(ValueError):
        ScoringWeights(sharpness=0.5, exposure=0.5, resolution=0.5)


# ---------------------------------------------------------------------------
# score_group
# ---------------------------------------------------------------------------

def test_score_group_empty():
    assert score_group({}) == []


def test_score_group_single_image():
    paths = _paths(1)
    result = score_group({paths[0]: _metrics()})
    assert len(result) == 1
    assert result[0].rank == 1
    assert result[0].score == 100.0


def test_score_group_returns_all_paths(tmp_path):
    paths = _paths(4)
    metrics = {p: _metrics(sharpness=float(i * 100)) for i, p in enumerate(paths)}
    scores = score_group(metrics)
    assert len(scores) == 4
    returned_paths = {s.path for s in scores}
    assert returned_paths == set(paths)


def test_score_group_rank_1_has_highest_score():
    paths = _paths(3)
    metrics = {
        paths[0]: _metrics(sharpness=500.0, exposure=90.0),  # clearly best
        paths[1]: _metrics(sharpness=100.0, exposure=50.0),
        paths[2]: _metrics(sharpness=10.0,  exposure=20.0),
    }
    scores = score_group(metrics)
    rank1 = next(s for s in scores if s.rank == 1)
    assert rank1.path == paths[0]
    assert rank1.score == max(s.score for s in scores)


def test_score_group_ranks_are_unique_and_sequential():
    paths = _paths(5)
    metrics = {p: _metrics(sharpness=float(i * 50)) for i, p in enumerate(paths)}
    scores = score_group(metrics)
    ranks = sorted(s.rank for s in scores)
    assert ranks == list(range(1, 6))


def test_score_group_scores_in_range():
    paths = _paths(4)
    metrics = {p: _metrics(sharpness=float(i * 100), exposure=float(i * 20))
               for i, p in enumerate(paths)}
    for s in score_group(metrics):
        assert 0.0 <= s.score <= 100.0


def test_score_group_reason_only_on_rank1():
    paths = _paths(3)
    metrics = {p: _metrics(sharpness=float(i * 100)) for i, p in enumerate(paths)}
    scores = score_group(metrics)
    rank1 = next(s for s in scores if s.rank == 1)
    others = [s for s in scores if s.rank != 1]
    assert rank1.reason != ""
    for s in others:
        assert s.reason == ""


def test_score_group_custom_weights():
    """Resolution-heavy weights should promote the highest-res image."""
    paths = _paths(2)
    metrics = {
        paths[0]: _metrics(sharpness=10.0,  resolution=10_000_000),  # low sharp, high res
        paths[1]: _metrics(sharpness=500.0, resolution=100_000),      # high sharp, low res
    }
    w = ScoringWeights(sharpness=0.05, exposure=0.05, resolution=0.90)
    scores = score_group(metrics, weights=w)
    rank1 = next(s for s in scores if s.rank == 1)
    assert rank1.path == paths[0]  # resolution winner should be picked


def test_score_group_identical_metrics_no_crash():
    """All images with identical metrics should not crash or divide by zero."""
    paths = _paths(3)
    m = _metrics()
    metrics = {p: m for p in paths}
    scores = score_group(metrics)
    assert len(scores) == 3
    for s in scores:
        assert 0.0 <= s.score <= 100.0
