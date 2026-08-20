"""
Test fixtures — dogfood tests use the real model on the real GPU; edge-case
tests never load it.

Reference images are the package's own bundled selftest assets
(``src/plain_sight/assets/selftest/``) so the suite runs from any checkout
without external workspace paths. Model cache resolves from the environment
(HF_HOME / HF_HUB_CACHE, or PLAIN_SIGHT_MODEL_DIR) — no hardcoded rig paths.
"""

import os
from pathlib import Path

import pytest

from PIL import Image, ImageDraw

from plain_sight.engine import Florence2Engine

ASSETS_DIR = (
    Path(__file__).resolve().parents[1] / "src" / "plain_sight" / "assets" / "selftest"
)


def make_text_image(path: str | Path, text: str = "STOP THE TRAIN 42") -> str:
    """Generate a simple text-bearing PNG with PIL. No committed binary."""
    dest = Path(path)
    img = Image.new("RGB", (480, 96), "white")
    draw = ImageDraw.Draw(img)
    draw.text((16, 28), text, fill="black")
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest)
    return str(dest)


def _asset(name: str) -> str:
    """Resolve a bundled reference image.

    A missing asset is a hard error, NOT a skip: these files are committed to
    the repo, so absence means a broken checkout — surface it loudly.
    """
    p = ASSETS_DIR / name
    if not p.is_file():
        raise FileNotFoundError(
            f"Bundled asset missing: {p}. Expected under src/plain_sight/assets/selftest/ "
            f"(committed to the repo)."
        )
    return str(p)


@pytest.fixture(scope="session")
def knight_png():
    return _asset("knight.png")


@pytest.fixture(scope="session")
def cheetah_jpg():
    return _asset("cheetah.jpg")


@pytest.fixture(scope="session")
def engine():
    """Session-scoped Florence-2 engine — loads the model once for all
    dogfood tests. Skips (not fails) when the model/GPU isn't available so
    the CI-safe suite stays runnable anywhere.
    """
    e = Florence2Engine(
        cache_dir=os.environ.get("PLAIN_SIGHT_MODEL_DIR") or None,
    )
    try:
        e._ensure_loaded()
    except (OSError, RuntimeError, ImportError) as exc:
        pytest.skip(f"Florence-2 model not available: {exc}")
    return e


@pytest.fixture()
def cold_engine():
    """Unloaded engine for validation-order tests. Never loads the model."""
    return Florence2Engine(device="cpu", dtype=None)


@pytest.fixture()
def text_image(tmp_path):
    return make_text_image(tmp_path / "stop_the_train.png")
