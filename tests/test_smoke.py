"""
Phase 1 smoke tests — verify basic project structure is importable and sane.
"""

import sys
from pathlib import Path

# Ensure src/ is on the path when running tests from the repo root
SRC = Path(__file__).parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def test_src_packages_importable():
    """All src sub-packages must be importable without errors."""
    import analysis  # noqa: F401
    import workers   # noqa: F401
    import export    # noqa: F401


def test_settings_defaults():
    """load_settings() returns expected default keys."""
    from config import load_settings, DEFAULTS

    settings = load_settings()
    for key in DEFAULTS:
        assert key in settings, f"Missing default key: {key}"


def test_settings_weights_sum_to_100():
    """Default scoring weights must sum to 100."""
    from config import DEFAULTS

    weights = DEFAULTS["weights"]
    assert sum(weights.values()) == 100


def test_sample_images_fixture(sample_images_dir):
    """Fixture creates readable image files."""
    from PIL import Image

    images = list(sample_images_dir.glob("*"))
    assert len(images) == 4

    for path in images:
        img = Image.open(path)
        img.verify()
