"""
Pure (no-Qt) file scanning and thumbnail generation.
Tested directly; ScanWorker wraps this in a QThread.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
)
THUMBNAIL_SIZE: tuple[int, int] = (160, 160)


@dataclass
class ImageInfo:
    path: Path
    file_size: int       # bytes on disk
    orig_width: int
    orig_height: int
    thumb: Image.Image   # RGBA PIL image, max 160×160


def enumerate_images(folder: Path) -> list[Path]:
    """Return all supported image paths under folder (recursive)."""
    return [
        p
        for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


def load_image_info(path: Path) -> ImageInfo:
    """
    Open an image file, generate a thumbnail, and return an ImageInfo.
    Raises OSError / UnidentifiedImageError on failure.
    """
    with Image.open(path) as img:
        orig_w, orig_h = img.size
        file_size = path.stat().st_size
        thumb = img.copy().convert("RGBA")

    thumb.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
    return ImageInfo(
        path=path,
        file_size=file_size,
        orig_width=orig_w,
        orig_height=orig_h,
        thumb=thumb,
    )
