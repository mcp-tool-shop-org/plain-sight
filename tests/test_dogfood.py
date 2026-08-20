"""
Dogfood tests — real Florence-2, real GPU, real inference. No mocks.

Marked ``dogfood``: CI runs only test_edge_cases.py. Run these locally with
``pytest tests/test_dogfood.py -v`` (first run downloads ~1.5 GB of weights).
"""

import pytest

pytestmark = pytest.mark.dogfood


class TestDescribe:
    def test_high_detail_is_a_paragraph(self, engine, cheetah_jpg):
        text = engine.describe(cheetah_jpg, detail="high")
        assert isinstance(text, str)
        assert len(text) >= 100  # more_detailed_caption is a full paragraph

    def test_subject_is_recognized(self, engine, cheetah_jpg):
        text = engine.describe(cheetah_jpg, detail="high").lower()
        assert any(k in text for k in ("cheetah", "leopard", "feline", "cat", "animal"))

    def test_tier_ordering(self, engine, knight_png):
        low = engine.describe(knight_png, detail="low")
        high = engine.describe(knight_png, detail="high")
        assert 0 < len(low) < len(high)

    def test_deterministic_repeat(self, engine, knight_png):
        # do_sample=False + beams: same image + tier => same caption.
        a = engine.describe(knight_png, detail="medium")
        b = engine.describe(knight_png, detail="medium")
        assert a == b

    def test_max_new_tokens_clips_output(self, engine, cheetah_jpg):
        clipped = engine.describe(cheetah_jpg, detail="high", max_new_tokens=12)
        full = engine.describe(cheetah_jpg, detail="high")
        assert len(clipped) < len(full)


class TestOcr:
    def test_ocr_returns_string(self, engine, knight_png):
        assert isinstance(engine.ocr(knight_png), str)

    def test_ocr_no_text_is_not_presented_as_verified(self, engine, knight_png):
        # GPU-only. Knight has no glyphs. Envelope must still qualify the
        # string -- we do not empty it, and we do not claim it was extracted.
        text = engine.ocr(knight_png)
        env = engine.ocr_envelope(text)
        assert env["text"] == text
        assert env["absence_of_text_unreliable"] is True
        assert env["revision_resolved"]

    def test_ocr_text_bearing_still_returns_the_text(self, engine, text_image):
        # GPU-only. A fix that refuses everything is not a fix.
        text = engine.ocr(text_image)
        assert any(tok in text for tok in ("STOP", "TRAIN", "42"))
        env = engine.ocr_envelope(text)
        assert env["absence_of_text_unreliable"] is True
        assert env["text"] == text


class TestSelftest:
    def test_selftest_passes(self, engine):
        result = engine.selftest()
        assert result["passed"] is True, result["checks"]
        assert len(result["checks"]) == 3


class TestSidecarE2E:
    def test_batch_writes_exact_basename_sidecar(self, engine, knight_png, tmp_path):
        import shutil

        from plain_sight.sidecars import compose_caption, sidecar_path_for

        img = tmp_path / "img_0042.png"
        shutil.copy(knight_png, img)

        caption = engine.describe(str(img), detail="low")
        sidecar = sidecar_path_for(img)
        sidecar.write_text(compose_caption("mcpt_style, ", caption, ""), encoding="utf-8")

        assert sidecar.name == "img_0042.txt"
        content = sidecar.read_text(encoding="utf-8")
        assert content.startswith("mcpt_style, ")
        assert len(content) > len("mcpt_style, ")
