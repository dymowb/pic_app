"""
Shared pytest fixtures.
"""

import pytest
from pathlib import Path


@pytest.fixture
def sample_images_dir(tmp_path: Path) -> Path:
    """Return a temp directory containing minimal valid JPEG and PNG stubs.

    Real pixel data is created via Pillow so the images are openable.
    """
    from PIL import Image

    img_dir = tmp_path / "images"
    img_dir.mkdir()

    for i in range(3):
        img = Image.new("RGB", (100, 100), color=(i * 80, 120, 200 - i * 60))
        img.save(img_dir / f"photo_{i}.jpg", format="JPEG")

    # Add a PNG
    img = Image.new("RGB", (200, 150), color=(10, 20, 30))
    img.save(img_dir / "photo_png.png", format="PNG")

    return img_dir
