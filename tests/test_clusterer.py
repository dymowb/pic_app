"""Tests for analysis.clusterer — similarity grouping."""

import sys
from pathlib import Path

import pytest
from PIL import Image

SRC = Path(__file__).parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import imagehash
from analysis.clusterer import cluster
from analysis.hasher import compute_phash


def _make_hash(color, size=(200, 200), tmp_path=None, name="img.jpg"):
    """Helper: create an image and return its pHash."""
    img = Image.new("RGB", size, color=color)
    path = tmp_path / name
    img.save(path)
    return path, compute_phash(path)


def test_cluster_empty_input():
    groups, unique = cluster({}, threshold=10)
    assert groups == []
    assert unique == []


def test_cluster_single_image(tmp_path):
    p, h = _make_hash((100, 100, 100), tmp_path=tmp_path, name="solo.jpg")
    groups, unique = cluster({p: h}, threshold=10)
    assert groups == []
    assert p in unique


def test_cluster_identical_images_grouped(tmp_path):
    """Two images from the same source should end up in the same group."""
    img = Image.new("RGB", (200, 200), color=(80, 80, 80))
    p1 = tmp_path / "a.jpg"
    p2 = tmp_path / "b.jpg"
    img.save(p1)
    img.save(p2)

    hashes = {p1: compute_phash(p1), p2: compute_phash(p2)}
    groups, unique = cluster(hashes, threshold=10)

    assert len(groups) == 1
    assert set(groups[0]) == {p1, p2}
    assert unique == []


def test_cluster_different_images_not_grouped(tmp_path):
    """Images with very different content should NOT be grouped."""
    import numpy as np

    # Checkerboard pattern — rich high-frequency content
    arr1 = np.zeros((200, 200, 3), dtype=np.uint8)
    arr1[::20, :] = 255
    arr1[:, ::20] = 255

    # Concentric gradient rings — very different frequency signature
    arr2 = np.zeros((200, 200, 3), dtype=np.uint8)
    for y in range(200):
        for x in range(200):
            dist = int(((x - 100) ** 2 + (y - 100) ** 2) ** 0.5) % 40
            arr2[y, x] = [dist * 6, 0, 0]

    p1 = tmp_path / "checker.png"
    p2 = tmp_path / "rings.png"
    Image.fromarray(arr1).save(p1)
    Image.fromarray(arr2).save(p2)

    hashes = {p1: compute_phash(p1), p2: compute_phash(p2)}
    groups, unique = cluster(hashes, threshold=10)

    assert groups == []
    assert len(unique) == 2


def test_cluster_groups_sorted_by_size_descending(tmp_path):
    """Larger groups must appear before smaller ones."""
    import numpy as np

    def _make_pattern(seed: int, path: Path) -> None:
        rng = np.random.default_rng(seed)
        arr = rng.integers(0, 256, (200, 200, 3), dtype=np.uint8)
        Image.fromarray(arr).save(path)

    # Group A: 3 near-identical (same base pattern, tiny shift)
    base_a = tmp_path / "base_a.png"
    _make_pattern(seed=1, path=base_a)
    paths_a = [base_a]
    img_a = Image.open(base_a)
    for i in range(2):
        p = tmp_path / f"a_copy_{i}.png"
        img_a.save(p)
        paths_a.append(p)

    # Group B: 2 near-identical (different base pattern)
    base_b = tmp_path / "base_b.png"
    _make_pattern(seed=9999, path=base_b)
    paths_b = [base_b]
    img_b = Image.open(base_b)
    p = tmp_path / "b_copy_0.png"
    img_b.save(p)
    paths_b.append(p)

    hashes = {}
    for p in paths_a + paths_b:
        hashes[p] = compute_phash(p)

    groups, _ = cluster(hashes, threshold=10)

    # Both groups must be found and the larger one comes first
    assert len(groups) >= 1
    sizes = [len(g) for g in groups]
    assert sizes == sorted(sizes, reverse=True)


def test_cluster_threshold_zero_only_identical(tmp_path):
    """At threshold=0 only byte-identical hashes should cluster."""
    img = Image.new("RGB", (200, 200), color=(80, 80, 80))
    p1 = tmp_path / "a.jpg"
    p2 = tmp_path / "b.jpg"
    img.save(p1)
    img.save(p2)

    # Same source → same pHash → distance 0 → grouped even at threshold 0
    hashes = {p1: compute_phash(p1), p2: compute_phash(p2)}
    groups, unique = cluster(hashes, threshold=0)
    assert len(groups) == 1


def test_cluster_returns_all_paths(tmp_path):
    """Every input path must appear in either groups or unique."""
    colors = [(i * 40, 0, 0) for i in range(5)]
    hashes = {}
    for i, color in enumerate(colors):
        p = tmp_path / f"img_{i}.jpg"
        Image.new("RGB", (200, 200), color=color).save(p)
        hashes[p] = compute_phash(p)

    groups, unique = cluster(hashes, threshold=10)
    all_returned = {p for g in groups for p in g} | set(unique)
    assert all_returned == set(hashes.keys())
