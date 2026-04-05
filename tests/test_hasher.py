"""Tests for analysis.hasher — perceptual hashing."""

import sys
from pathlib import Path

import pytest
from PIL import Image

SRC = Path(__file__).parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import imagehash
from analysis.hasher import compute_phash, hamming_distance


def _save_image(path: Path, color=(128, 128, 128), size=(100, 100)) -> Path:
    Image.new("RGB", size, color=color).save(path)
    return path


def test_compute_phash_returns_imagehash(tmp_path):
    path = _save_image(tmp_path / "img.jpg")
    h = compute_phash(path)
    assert isinstance(h, imagehash.ImageHash)


def test_identical_images_have_zero_distance(tmp_path):
    """Two identical images must produce hashes with distance 0."""
    path = _save_image(tmp_path / "img.jpg", color=(200, 100, 50))
    h1 = compute_phash(path)
    h2 = compute_phash(path)
    assert hamming_distance(h1, h2) == 0


def test_different_images_have_nonzero_distance(tmp_path):
    """Visually different images should have a non-zero distance."""
    p1 = _save_image(tmp_path / "black.jpg", color=(0, 0, 0), size=(200, 200))
    p2 = _save_image(tmp_path / "white.jpg", color=(255, 255, 255), size=(200, 200))
    h1 = compute_phash(p1)
    h2 = compute_phash(p2)
    assert hamming_distance(h1, h2) > 0


def test_similar_images_have_low_distance(tmp_path):
    """Near-identical images (tiny brightness shift) have a small distance."""
    img1 = Image.new("RGB", (200, 200), color=(100, 100, 100))
    img2 = Image.new("RGB", (200, 200), color=(102, 102, 102))  # very slight change
    p1 = tmp_path / "a.jpg"
    p2 = tmp_path / "b.jpg"
    img1.save(p1)
    img2.save(p2)

    h1 = compute_phash(p1)
    h2 = compute_phash(p2)
    assert hamming_distance(h1, h2) <= 5


def test_compute_phash_raises_on_missing_file(tmp_path):
    with pytest.raises(Exception):
        compute_phash(tmp_path / "nonexistent.jpg")


def test_compute_phash_raises_on_corrupt_file(tmp_path):
    bad = tmp_path / "bad.jpg"
    bad.write_bytes(b"\xff\xd8\xff" + b"\x00" * 10)
    with pytest.raises(Exception):
        compute_phash(bad)


def test_hamming_distance_is_symmetric(tmp_path):
    p1 = _save_image(tmp_path / "a.jpg", color=(10, 20, 30))
    p2 = _save_image(tmp_path / "b.jpg", color=(200, 180, 160))
    h1, h2 = compute_phash(p1), compute_phash(p2)
    assert hamming_distance(h1, h2) == hamming_distance(h2, h1)
