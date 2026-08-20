"""
CI-safe edge-case tests — no model, no GPU, no network.

Covers the validation layer (which must fire BEFORE any model load), the
sidecar/template contract, path expansion, and CLI argument parsing. Every
test here must pass on a bare checkout with only the dev dependencies.
"""

import pytest

from plain_sight.engine import (
    DETAIL_TASKS,
    MAX_NEW_TOKENS_CEILING,
    OCR_TASK,
)
from plain_sight.cli import build_parser
from plain_sight.sidecars import (
    IMAGE_EXTS,
    compose_caption,
    iter_image_files,
    sidecar_path_for,
)


# ---------------------------------------------------------------------------
# Engine validation — must reject bad input WITHOUT loading the model
# ---------------------------------------------------------------------------

class TestValidationBeforeLoad:
    def test_unknown_detail_rejected_cold(self, cold_engine, tmp_path):
        img = tmp_path / "x.png"
        img.write_bytes(b"not a real png")
        with pytest.raises(ValueError, match="detail tier"):
            cold_engine.describe(str(img), detail="ultra")
        assert not cold_engine.loaded

    def test_missing_file_rejected_cold(self, cold_engine):
        with pytest.raises(FileNotFoundError):
            cold_engine.describe("Z:/nope/never/missing.png")
        assert not cold_engine.loaded

    def test_directory_rejected_cold(self, cold_engine, tmp_path):
        with pytest.raises(FileNotFoundError, match="not a file"):
            cold_engine.describe(str(tmp_path))
        assert not cold_engine.loaded

    @pytest.mark.parametrize("bad", [0, -1, MAX_NEW_TOKENS_CEILING + 1])
    def test_max_new_tokens_bounds(self, cold_engine, bad, tmp_path):
        img = tmp_path / "x.png"
        img.write_bytes(b"stub")
        with pytest.raises(ValueError, match="max_new_tokens"):
            cold_engine.describe(str(img), max_new_tokens=bad)
        assert not cold_engine.loaded

    def test_max_new_tokens_bool_rejected(self, cold_engine):
        with pytest.raises(ValueError, match="integer"):
            cold_engine._validate_max_new_tokens(True)

    def test_max_new_tokens_none_uses_default(self, cold_engine):
        assert cold_engine._validate_max_new_tokens(None) >= 1

    def test_ocr_missing_file_rejected_cold(self, cold_engine):
        with pytest.raises(FileNotFoundError):
            cold_engine.ocr("Z:/nope/missing.png")
        assert not cold_engine.loaded


class TestDetailLadder:
    def test_three_tiers(self):
        assert set(DETAIL_TASKS) == {"low", "medium", "high"}

    def test_tier_tokens_match_florence_tasks(self):
        assert DETAIL_TASKS["low"] == "<CAPTION>"
        assert DETAIL_TASKS["medium"] == "<DETAILED_CAPTION>"
        assert DETAIL_TASKS["high"] == "<MORE_DETAILED_CAPTION>"
        assert OCR_TASK == "<OCR>"

    def test_dtype_normalization(self):
        from plain_sight.engine import Florence2Engine

        assert Florence2Engine(device="cpu", dtype="float32").dtype is None
        assert Florence2Engine(device="cpu", dtype="none").dtype is None
        assert Florence2Engine(device="cpu", dtype="float16").dtype == "float16"


# ---------------------------------------------------------------------------
# Sidecar / template contract
# ---------------------------------------------------------------------------

class TestSidecarContract:
    def test_exact_basename_pairing(self, tmp_path):
        assert sidecar_path_for(tmp_path / "img_0042.png").name == "img_0042.txt"

    def test_no_counter_suffix(self, tmp_path):
        # The whole point vs the cloud SaveText node: no _00001 counter.
        assert "_0000" not in sidecar_path_for(tmp_path / "hero.png").name

    def test_sidecar_next_to_image_by_default(self, tmp_path):
        assert sidecar_path_for(tmp_path / "a" / "b.png").parent == tmp_path / "a"

    def test_out_dir_override(self, tmp_path):
        out = tmp_path / "caps"
        p = sidecar_path_for(tmp_path / "imgs" / "b.png", out)
        assert p == out / "b.txt"

    def test_dotted_stem(self, tmp_path):
        assert sidecar_path_for(tmp_path / "v1.2.final.png").name == "v1.2.final.txt"

    def test_compose_is_bare_concatenation(self):
        assert compose_caption("pre", "cap", "post") == "precappost"

    def test_compose_injects_no_delimiter(self):
        assert compose_caption("", "caption", "") == "caption"

    def test_compose_trigger_token_pattern(self):
        assert compose_caption("mcpt_style, ", "a knight", "") == "mcpt_style, a knight"


class TestIterImageFiles:
    def test_directory_filters_extensions(self, tmp_path):
        (tmp_path / "a.png").write_bytes(b"x")
        (tmp_path / "b.jpg").write_bytes(b"x")
        (tmp_path / "notes.txt").write_text("x")
        (tmp_path / "c.PNG").write_bytes(b"x")  # case-insensitive
        found = iter_image_files([tmp_path])
        names = [p.name for p in found]
        assert names == sorted(["a.png", "b.jpg", "c.PNG"])
        assert "notes.txt" not in names

    def test_explicit_file_passed_through(self, tmp_path):
        odd = tmp_path / "frame.webp"
        odd.write_bytes(b"x")
        assert iter_image_files([odd]) == [odd]

    def test_missing_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            iter_image_files([tmp_path / "ghost"])

    def test_empty_input_raises(self):
        with pytest.raises(ValueError):
            iter_image_files([])

    def test_mixed_files_and_dirs(self, tmp_path):
        d = tmp_path / "d"
        d.mkdir()
        (d / "in_dir.png").write_bytes(b"x")
        loose = tmp_path / "loose.jpg"
        loose.write_bytes(b"x")
        found = iter_image_files([loose, d])
        assert [p.name for p in found] == ["loose.jpg", "in_dir.png"]

    def test_known_extensions_are_lowercase_keys(self):
        assert all(e == e.lower() for e in IMAGE_EXTS)


# ---------------------------------------------------------------------------
# CLI parsing (no engine construction, no model)
# ---------------------------------------------------------------------------

class TestCliParser:
    def test_describe_defaults(self):
        args = build_parser().parse_args(["describe", "img.png"])
        assert args.command == "describe"
        assert args.detail == "high"
        assert args.max_new_tokens is None

    def test_batch_flags(self):
        args = build_parser().parse_args([
            "batch", "dir1", "img.png",
            "--prefix", "trig, ", "--suffix", " end",
            "--out-dir", "caps", "--overwrite", "--detail", "low",
        ])
        assert args.paths == ["dir1", "img.png"]
        assert args.prefix == "trig, "
        assert args.suffix == " end"
        assert args.overwrite is True
        assert args.detail == "low"

    def test_invalid_detail_is_user_error_exit_1(self):
        # Studio exit-code canon: usage errors are USER errors (1), not
        # argparse's native 2 (which the canon reserves for runtime errors).
        with pytest.raises(SystemExit) as exc:
            build_parser().parse_args(["describe", "img.png", "--detail", "ultra"])
        assert exc.value.code == 1

    def test_missing_command_is_user_error_exit_1(self):
        with pytest.raises(SystemExit) as exc:
            build_parser().parse_args([])
        assert exc.value.code == 1

    def test_ocr_and_utility_commands_parse(self):
        assert build_parser().parse_args(["ocr", "x.png"]).command == "ocr"
        assert build_parser().parse_args(["status"]).command == "status"
        assert build_parser().parse_args(["selftest"]).command == "selftest"
