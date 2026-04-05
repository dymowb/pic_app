"""
Perceptual hashing — compute a 64-bit pHash for an image file.
Pure Python, no Qt dependency.
"""

from __future__ import annotations

from pathlib import Path

import imagehash
from PIL import Image, UnidentifiedImageError


def compute_phash(path: Path) -> imagehash.ImageHash:
    """
    Return the 64-bit perceptual hash (pHash) for the image at path.

    Raises
    ------
    UnidentifiedImageError  if Pillow cannot identify the file format.
    OSError                 if the file cannot be opened.
    ValueError              if path does not point to a readable image.
    """
    with Image.open(path) as img:
        # Force a full pixel load before closing the file handle.
        # Pillow uses lazy loading — without this, imagehash.phash() can
        # receive an unloaded image and hang (especially on Windows).
        img.load()
        # Convert to RGB to normalise palette / CMYK / RGBA modes.
        rgb = img.convert("RGB")

    return imagehash.phash(rgb, hash_size=8)  # 8×8 = 64-bit hash


def hamming_distance(a: imagehash.ImageHash, b: imagehash.ImageHash) -> int:
    """Return the Hamming distance between two pHashes (0 = identical)."""
    return a - b
