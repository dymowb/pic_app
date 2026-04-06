"""
Tests for analysis.scanner — pure scanning logic (no Qt required).
"""

import sys
from pathlib import Path

import pytest
from PIL import Image

SRC = Path(__file__).parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from analysis.scanner import enumerate_images, load_image_info, SUPPORTED_EXTENSIONS


def _make_images(folder: Path, count: int = 4) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(count):
        p = folder / f"img_{i}.jpg"
        Image.new("RGB", (200, 200), color=(i * 60, 100, 200)).save(p)
        paths.append(p)
    return paths


def test_enumerate_images_finds_supported(tmp_path):
    _make_images(tmp_path, count=3)
    (tmp_path / "notes.txt").write_text("not an image")
    (tmp_path / "thumb.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    )

    paths = enumerate_images(tmp_path)
    suffixes = {p.suffix.lower() for p in paths}
    assert ".txt" not in suffixes
    assert all(s in SUPPORTED_EXTENSIONS for s in suffixes)


def test_enumerate_images_recursive(tmp_path):
    sub = tmp_path / "trip" / "raw"
    sub.mkdir(parents=True)
    Image.new("RGB", (10, 10)).save(tmp_path / "root.jpg")
    Image.new("RGB", (10, 10)).save(sub / "deep.png")

    paths = enumerate_images(tmp_path)
    names = {p.name for p in paths}
    assert "root.jpg" in names
    assert "deep.png" in names


def test_enumerate_images_empty_folder(tmp_path):
    assert enumerate_images(tmp_path) == []


def test_load_image_info_basic(tmp_path):
    path = tmp_path / "test.jpg"
    Image.new("RGB", (400, 300), color=(10, 20, 30)).save(path)

    info = load_image_info(path)

    assert info.path == path
    assert info.orig_width == 400
    assert info.orig_height == 300
    assert info.file_size == path.stat().st_size
    assert info.file_size > 0
    assert info.thumb.width <= 160
    assert info.thumb.height <= 160
    assert info.thumb.mode == "RGBA"


def test_load_image_info_preserves_aspect_ratio(tmp_path):
    path = tmp_path / "wide.jpg"
    Image.new("RGB", (800, 200)).save(path)

    info = load_image_info(path)
    ratio_orig = 800 / 200
    ratio_thumb = info.thumb.width / info.thumb.height
    assert abs(ratio_orig - ratio_thumb) < 0.1


def test_load_image_info_raises_on_corrupt(tmp_path):
    path = tmp_path / "bad.jpg"
    path.write_bytes(b"\xff\xd8\xff" + b"\x00" * 10)

    with pytest.raises(Exception):
        load_image_info(path)


def test_load_image_info_png(tmp_path):
    path = tmp_path / "image.png"
    Image.new("RGBA", (100, 100), color=(255, 0, 0, 128)).save(path)

    info = load_image_info(path)
    assert info.orig_width == 100
    assert info.thumb.mode == "RGBA"
