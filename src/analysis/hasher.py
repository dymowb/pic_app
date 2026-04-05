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
        return imagehash.phash(img, hash_size=8)  # 8×8 = 64-bit hash


def hamming_distance(a: imagehash.ImageHash, b: imagehash.ImageHash) -> int:
    """Return the Hamming distance between two pHashes (0 = identical)."""
    return a - b
