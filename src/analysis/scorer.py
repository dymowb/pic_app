"""
Scoring & Recommendation Engine — pure Python, no Qt dependency.

For each duplicate group:
  1. Normalise each quality metric within the group (0–1 range)
  2. Apply user-configurable weights to get a composite score (0–100)
  3. Rank images by score
  4. Generate a plain-English reason for the top pick

Metrics used
------------
sharpness   — Laplacian variance (higher = sharper, unbounded → normalised)
exposure    — 0–100 score (higher = better exposed)
noise       — 0–100 score (higher = cleaner)
resolution  — total pixels (higher = more detail → normalised)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from analysis.quality import ImageMetrics


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ScoringWeights:
    sharpness: float = 0.50
    exposure: float = 0.30
    resolution: float = 0.20

    def __post_init__(self) -> None:
        total = self.sharpness + self.exposure + self.resolution
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Weights must sum to 1.0, got {total:.3f}. "
                "Pass values as fractions, e.g. sharpness=0.5."
            )

    @classmethod
    def from_percent(cls, sharpness: int, exposure: int, resolution: int) -> "ScoringWeights":
        """Convenience: pass integer percentages (must sum to 100)."""
        return cls(
            sharpness=sharpness / 100,
            exposure=exposure / 100,
            resolution=resolution / 100,
        )


@dataclass
class ImageScore:
    path: Path
    score: float        # composite 0–100
    rank: int           # 1 = best in group
    reason: str         # plain-English explanation for rank-1


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------

def score_group(
    metrics: dict[Path, ImageMetrics],
    weights: ScoringWeights | None = None,
) -> list[ImageScore]:
    """
    Score and rank all images in a duplicate group.

    Parameters
    ----------
    metrics  : {path: ImageMetrics} for every image in the group
    weights  : scoring weights; defaults to ScoringWeights()

    Returns
    -------
    List of ImageScore sorted by score descending (rank 1 = best).
    """
    if weights is None:
        weights = ScoringWeights()

    paths = list(metrics.keys())
    if not paths:
        return []

    if len(paths) == 1:
        return [ImageScore(paths[0], 100.0, 1, "Only image in group")]

    # ── Normalise each metric within the group ───────────────────────
    def _norm(values: list[float]) -> list[float]:
        lo, hi = min(values), max(values)
        if hi == lo:
            return [1.0] * len(values)
        return [(v - lo) / (hi - lo) for v in values]

    sharpness_vals  = [metrics[p].sharpness  for p in paths]
    exposure_vals   = [metrics[p].exposure   for p in paths]
    noise_vals      = [metrics[p].noise      for p in paths]  # already 0–100
    resolution_vals = [float(metrics[p].resolution) for p in paths]

    norm_sharp  = _norm(sharpness_vals)
    norm_exp    = _norm(exposure_vals)
    norm_noise  = _norm(noise_vals)
    norm_res    = _norm(resolution_vals)

    # ── Composite score ────────────────────────────────────
    # noise is folded into sharpness weight equally (noise is a sharpness proxy)
    sharp_weight = weights.sharpness * 0.7
    noise_weight = weights.sharpness * 0.3

    raw_scores: list[float] = []
    for i in range(len(paths)):
        s = (
            sharp_weight  * norm_sharp[i]
            + noise_weight  * norm_noise[i]
            + weights.exposure    * norm_exp[i]
            + weights.resolution  * norm_res[i]
        )
        raw_scores.append(s)

    # Rescale to 0–100
    lo, hi = min(raw_scores), max(raw_scores)
    if hi > lo:
        scores_100 = [(s - lo) / (hi - lo) * 100 for s in raw_scores]
    else:
        scores_100 = [50.0] * len(raw_scores)

    # ── Rank ──────────────────────────────────────────
    indexed = sorted(
        enumerate(scores_100), key=lambda x: x[1], reverse=True
    )

    results: list[ImageScore] = []
    for rank, (i, score) in enumerate(indexed, start=1):
        reason = _reason(rank, i, norm_sharp, norm_exp, norm_res, norm_noise, weights)
        results.append(ImageScore(
            path=paths[i],
            score=round(score, 1),
            rank=rank,
            reason=reason,
        ))

    return results


# ---------------------------------------------------------------------------
# Reason generation
# ---------------------------------------------------------------------------

_REASON_TEMPLATES = {
    "sharpness":  "Sharpest image in this group",
    "exposure":   "Best exposure — well-balanced brightness",
    "resolution": "Highest resolution in this group",
    "noise":      "Cleanest image — lowest noise",
    "balanced":   "Best overall quality score",
}


def _reason(
    rank: int,
    idx: int,
    norm_sharp: list[float],
    norm_exp: list[float],
    norm_res: list[float],
    norm_noise: list[float],
    weights: ScoringWeights,
) -> str:
    if rank != 1:
        return ""

    # Weighted contributions for this image
    contributions = {
        "sharpness":  weights.sharpness * 0.7 * norm_sharp[idx],
        "noise":      weights.sharpness * 0.3 * norm_noise[idx],
        "exposure":   weights.exposure  * norm_exp[idx],
        "resolution": weights.resolution * norm_res[idx],
    }

    dominant = max(contributions, key=contributions.get)

    # Only call it dominant if it has a clear lead (> 10% margin)
    vals = sorted(contributions.values(), reverse=True)
    if len(vals) >= 2 and vals[0] - vals[1] < 0.05:
        dominant = "balanced"

    return _REASON_TEMPLATES.get(dominant, _REASON_TEMPLATES["balanced"])
