"""
CI-safe edge-case tests — no model, no GPU, no network.

Covers the validation layer (which must fire BEFORE any model load), the
sidecar/template contract, path expansion, and CLI argument parsing. Every
test here must pass on a bare checkout with only the dev dependencies.
"""

import importlib
import json
import logging
import os
from pathlib import Path

import pytest

from plain_sight.engine import (
    DETAIL_TASKS,
    MAX_NEW_TOKENS_CEILING,
    OCR_ABSENCE_NOTE,
    OCR_TASK,
    PINNED_MODEL_REVISION,
    Florence2Engine,
)
from plain_sight.cli import build_parser, main, _err
from plain_sight.sidecars import (
    IMAGE_EXTS,
    compose_caption,
    find_sidecar_collisions,
    iter_image_files,
    manifest_collides_with_sidecars,
    sidecar_is_complete,
    sidecar_path_for,
    write_batch_manifest,
    write_sidecar_atomic,
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


# ---------------------------------------------------------------------------
# Wave 1 regressions — PS-001 through PS-004 (CI-safe, no model load)
# ---------------------------------------------------------------------------

@pytest.fixture
def restore_logger():
    """Logging state is global; snapshot and restore around each test."""
    log = logging.getLogger("plain_sight")
    old_level = log.level
    old_handlers = list(log.handlers)
    old_propagate = log.propagate
    yield log
    log.setLevel(old_level)
    for handler in list(log.handlers):
        log.removeHandler(handler)
    for handler in old_handlers:
        log.addHandler(handler)
    log.propagate = old_propagate


class TestModelIdEnv:
    """PS-001: DEFAULT_MODEL_ID must honour PLAIN_SIGHT_MODEL_ID at import time."""

    def test_env_set_is_honoured(self, monkeypatch):
        monkeypatch.setenv("PLAIN_SIGHT_MODEL_ID", "some-other/model")
        import plain_sight.engine as engine_mod
        importlib.reload(engine_mod)
        try:
            assert engine_mod.DEFAULT_MODEL_ID == "some-other/model"
            assert engine_mod.Florence2Engine().model_id == "some-other/model"
            assert not engine_mod.Florence2Engine().loaded
        finally:
            monkeypatch.delenv("PLAIN_SIGHT_MODEL_ID", raising=False)
            importlib.reload(engine_mod)

    def test_unset_falls_back_to_community_large(self, monkeypatch):
        monkeypatch.delenv("PLAIN_SIGHT_MODEL_ID", raising=False)
        import plain_sight.engine as engine_mod
        importlib.reload(engine_mod)
        try:
            assert engine_mod.DEFAULT_MODEL_ID == "florence-community/Florence-2-large"
            assert engine_mod.Florence2Engine().model_id == "florence-community/Florence-2-large"
        finally:
            importlib.reload(engine_mod)


class TestConfigureLogging:
    """PS-002: PLAIN_SIGHT_LOG_LEVEL is a real knob, idempotent, stderr-only."""

    def test_debug_is_honoured(self, monkeypatch, restore_logger):
        monkeypatch.setenv("PLAIN_SIGHT_LOG_LEVEL", "DEBUG")
        from plain_sight.engine import configure_logging

        level = configure_logging()
        assert level == logging.DEBUG
        assert restore_logger.isEnabledFor(logging.DEBUG)

    def test_unrecognised_falls_back_to_warning(self, monkeypatch, restore_logger):
        monkeypatch.setenv("PLAIN_SIGHT_LOG_LEVEL", "NONSENSE")
        from plain_sight.engine import configure_logging

        level = configure_logging()
        assert level == logging.WARNING

    def test_second_call_does_not_add_a_handler(self, monkeypatch, restore_logger):
        monkeypatch.setenv("PLAIN_SIGHT_LOG_LEVEL", "INFO")
        from plain_sight.engine import configure_logging

        configure_logging()
        n = len(restore_logger.handlers)
        configure_logging()
        assert len(restore_logger.handlers) == n == 1


class TestSidecarCollisions:
    """PS-003: same-stem images must refuse, never silently skip-mislabel."""

    def test_distinct_stems_are_safe(self, tmp_path):
        a = tmp_path / "a.png"
        b = tmp_path / "b.jpg"
        assert find_sidecar_collisions([a, b]) == {}

    def test_single_image_is_safe(self, tmp_path):
        assert find_sidecar_collisions([tmp_path / "only.png"]) == {}

    def test_empty_list_is_safe(self):
        assert find_sidecar_collisions([]) == {}

    def test_same_folder_png_and_jpg_collide(self, tmp_path):
        png = tmp_path / "img.png"
        jpg = tmp_path / "img.jpg"
        collisions = find_sidecar_collisions([png, jpg])
        assert len(collisions) == 1
        (sidecar, claimants) = next(iter(collisions.items()))
        assert sidecar.name == "img.txt"
        assert set(claimants) == {png, jpg}

    def test_out_dir_collapses_stems_from_two_folders(self, tmp_path):
        a = tmp_path / "a" / "img.png"
        b = tmp_path / "b" / "img.png"
        caps = tmp_path / "caps"
        collisions = find_sidecar_collisions([a, b], out_dir=caps)
        assert len(collisions) == 1
        (sidecar, claimants) = next(iter(collisions.items()))
        assert sidecar == caps / "img.txt"
        assert set(claimants) == {a, b}

    def test_three_way_collision_lists_all(self, tmp_path):
        files = [tmp_path / f"img{ext}" for ext in (".png", ".jpg", ".webp")]
        collisions = find_sidecar_collisions(files)
        assert len(collisions) == 1
        claimants = next(iter(collisions.values()))
        assert set(claimants) == set(files)

    def test_cli_batch_refuses_before_write_or_load(self, tmp_path, capsys):
        (tmp_path / "img.png").write_bytes(b"stub")
        (tmp_path / "img.jpg").write_bytes(b"stub")
        code = main(["batch", str(tmp_path)])
        captured = capsys.readouterr()
        assert code == 1
        assert "SIDECAR_COLLISION" in captured.err
        first = captured.err.splitlines()[0]
        first.encode("ascii")  # H-02: would have caught the em-dash in the hint
        assert "img.png" in captured.err
        assert "img.jpg" in captured.err
        assert list(tmp_path.glob("*.txt")) == []


class TestBatchContinuesOnRuntimeError:
    """PS-004: one RuntimeError must not abort the batch or swallow the summary."""

    def test_runtime_error_on_one_image_is_partial_success(self, tmp_path, monkeypatch, capsys):
        good = tmp_path / "good.png"
        bad = tmp_path / "bad.png"
        good.write_bytes(b"stub")
        bad.write_bytes(b"stub")

        def fake_describe(self, image_path, detail="high", max_new_tokens=None):
            if image_path.endswith("bad.png"):
                raise RuntimeError("simulated OOM")
            return "a caption"

        monkeypatch.setattr("plain_sight.cli.Florence2Engine.describe", fake_describe)
        code = main(["batch", str(tmp_path)])
        captured = capsys.readouterr()
        assert code == 3
        assert '"failed": 1' in captured.out
        assert '"written": 1' in captured.out
        assert (tmp_path / "good.txt").read_text(encoding="utf-8") == "a caption"
        assert not (tmp_path / "bad.txt").exists()

    def test_keyboardinterrupt_is_not_swallowed_as_item_failure(
        self, tmp_path, monkeypatch, capsys
    ):
        # The batch loop must not catch KeyboardInterrupt (it is not Exception).
        # main() then maps it to the existing INTERRUPTED user-error path.
        img = tmp_path / "only.png"
        img.write_bytes(b"stub")

        def boom(self, image_path, detail="high", max_new_tokens=None):
            raise KeyboardInterrupt

        monkeypatch.setattr("plain_sight.cli.Florence2Engine.describe", boom)
        code = main(["batch", str(tmp_path)])
        captured = capsys.readouterr()
        assert code == 1
        assert "INTERRUPTED" in captured.err
        assert '"failed"' not in captured.out
        assert list(tmp_path.glob("*.txt")) == []


class TestEngineCtorInsideErrorBoundary:
    """B-01: load failure is a structured runtime error, not a raw stack at exit 1.

    Would have caught: Florence2Engine() sitting above main()'s try (and MCP
    import dying on PLAIN_SIGHT_EAGER_LOAD + a bad MODEL_ID).
    """

    def test_cli_eager_load_failure_is_internal_exit_2(self, monkeypatch, capsys):
        def boom(self):
            raise OSError("repo not found")

        monkeypatch.setenv("PLAIN_SIGHT_EAGER_LOAD", "1")
        monkeypatch.setattr("plain_sight.cli.Florence2Engine._ensure_loaded", boom)
        code = main(["status"])
        captured = capsys.readouterr()
        assert code == 2
        assert "INTERNAL" in captured.err
        assert "Traceback" not in captured.err

    def test_mcp_import_survives_eager_bad_id(self, monkeypatch):
        def boom(self):
            raise OSError("repo not found")

        monkeypatch.setenv("PLAIN_SIGHT_EAGER_LOAD", "1")
        monkeypatch.setenv("PLAIN_SIGHT_MODEL_ID", "definitely-not/a-real-model")
        monkeypatch.setattr(
            "plain_sight.engine.Florence2Engine._ensure_loaded", boom
        )
        import plain_sight.server as server_mod
        importlib.reload(server_mod)
        try:
            assert server_mod.engine is not None
            assert server_mod.engine.loaded is False
            from fastmcp.exceptions import ToolError

            status = server_mod.sight_status()
            assert status["loaded"] is False
            assert status.get("eager_load_attempted") is True
            assert "repo not found" in status["eager_load_error"]
            with pytest.raises(ToolError, match="repo not found"):
                server_mod._ensure_model()
            # status must not have triggered a retry/load
            assert server_mod.engine.loaded is False
        finally:
            monkeypatch.delenv("PLAIN_SIGHT_EAGER_LOAD", raising=False)
            monkeypatch.delenv("PLAIN_SIGHT_MODEL_ID", raising=False)
            importlib.reload(server_mod)


class TestMcpEagerLoadEnv:
    """H-01: PLAIN_SIGHT_EAGER_LOAD is honoured on MCP without killing import.

    Would have caught: server.py hardcoding eager_load=False with no follow-up
    load, so the documented env var was dead.
    """

    def test_eager_true_loads_at_import(self, monkeypatch):
        calls = {"n": 0}

        def fake_load(self):
            calls["n"] += 1

            class Dummy:
                config = object()

                def parameters(self):
                    return []

            self._model = Dummy()
            self._processor = object()

        monkeypatch.setenv("PLAIN_SIGHT_EAGER_LOAD", "1")
        monkeypatch.setattr(
            "plain_sight.engine.Florence2Engine._ensure_loaded", fake_load
        )
        import plain_sight.server as server_mod
        importlib.reload(server_mod)
        try:
            assert server_mod.engine.loaded is True
            assert calls["n"] == 1
            before = calls["n"]
            status = server_mod.sight_status()
            assert status["loaded"] is True
            assert calls["n"] == before  # status never loads
        finally:
            monkeypatch.delenv("PLAIN_SIGHT_EAGER_LOAD", raising=False)
            importlib.reload(server_mod)

    def test_eager_unset_does_not_load(self, monkeypatch):
        calls = {"n": 0}

        def fake_load(self):
            calls["n"] += 1
            self._model = object()
            self._processor = object()

        monkeypatch.delenv("PLAIN_SIGHT_EAGER_LOAD", raising=False)
        monkeypatch.setattr(
            "plain_sight.engine.Florence2Engine._ensure_loaded", fake_load
        )
        import plain_sight.server as server_mod
        importlib.reload(server_mod)
        try:
            assert server_mod.engine.loaded is False
            assert calls["n"] == 0
            status = server_mod.sight_status()
            assert status["loaded"] is False
            assert "PLAIN_SIGHT_EAGER_LOAD=1" in status["note"]
            assert calls["n"] == 0
        finally:
            importlib.reload(server_mod)


class TestRevisionPin:
    """B-03a/b: default revision is pinned; env overrides; status is split.

    Would have caught: DEFAULT_MODEL_REVISION = None, and status() omitting
    requested vs resolved (or raising on a missing _commit_hash).
    """

    def test_constructed_engine_requests_the_pin(self, monkeypatch):
        monkeypatch.delenv("PLAIN_SIGHT_MODEL_REVISION", raising=False)
        import plain_sight.engine as engine_mod
        importlib.reload(engine_mod)
        try:
            e = engine_mod.Florence2Engine(device="cpu", dtype=None, eager_load=False)
            assert e.revision == PINNED_MODEL_REVISION
            status = e.status()
            assert status["revision_requested"] == PINNED_MODEL_REVISION
            assert status["revision_resolved"] is None  # not loaded
            assert e.loaded is False
        finally:
            importlib.reload(engine_mod)

    def test_env_override_changes_requested(self, monkeypatch):
        monkeypatch.setenv("PLAIN_SIGHT_MODEL_REVISION", "abc123deadbeef")
        import plain_sight.engine as engine_mod
        importlib.reload(engine_mod)
        try:
            e = engine_mod.Florence2Engine(device="cpu", dtype=None, eager_load=False)
            assert e.revision == "abc123deadbeef"
            assert e.status()["revision_requested"] == "abc123deadbeef"
        finally:
            monkeypatch.delenv("PLAIN_SIGHT_MODEL_REVISION", raising=False)
            importlib.reload(engine_mod)

    def test_resolved_degrades_when_commit_hash_missing(self, cold_engine):
        class Dummy:
            config = object()  # no _commit_hash

            def parameters(self):
                return []

        cold_engine._model = Dummy()
        status = cold_engine.status()
        assert status["revision_resolved"] is None


class TestBatchManifest:
    """B-03c: opt-in explicit path; collision refused before load/write.

    Would have caught: a batch that writes a provenance file with no flag,
    or a manifest path that overwrites a sidecar.
    """

    def test_no_manifest_without_flag(self, tmp_path, monkeypatch):
        img = tmp_path / "a.png"
        img.write_bytes(b"stub")
        monkeypatch.setattr(
            "plain_sight.cli.Florence2Engine.describe",
            lambda self, *a, **k: "caption",
        )
        code = main(["batch", str(img)])
        assert code == 0
        json_files = list(tmp_path.glob("*.json")) + list(tmp_path.rglob("*.json"))
        assert json_files == []
        assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "caption"

    def test_manifest_round_trips(self, tmp_path, monkeypatch):
        img = tmp_path / "a.png"
        img.write_bytes(b"stub")
        man = tmp_path / "run.json"
        monkeypatch.setattr(
            "plain_sight.cli.Florence2Engine.describe",
            lambda self, *a, **k: "caption",
        )
        code = main(["batch", str(img), "--prefix", "trig, ", "--manifest", str(man)])
        assert code == 0
        payload = json.loads(man.read_text(encoding="utf-8"))
        for key in (
            "plain_sight_version", "torch_version", "transformers_version",
            "model_id", "revision_requested", "revision_resolved",
            "device", "dtype", "num_beams", "detail", "max_new_tokens",
            "prefix", "suffix", "total", "written", "skipped_existing", "failed",
            "images", "created_at",
        ):
            assert key in payload, key
        assert payload["prefix"] == "trig, "
        assert payload["written"] == 1
        assert payload["images"][0]["status"] == "written"

    def test_manifest_collision_refused_before_write(self, tmp_path, monkeypatch):
        img = tmp_path / "a.png"
        img.write_bytes(b"stub")
        # Sidecar would be a.txt — collide the manifest onto it.
        called = {"n": 0}

        def fake_describe(self, *a, **k):
            called["n"] += 1
            return "caption"

        monkeypatch.setattr("plain_sight.cli.Florence2Engine.describe", fake_describe)
        code = main(["batch", str(img), "--manifest", str(tmp_path / "a.txt")])
        captured_fail = called["n"]
        assert code == 1
        assert captured_fail == 0
        assert not (tmp_path / "a.txt").exists()

    def test_mcp_manifest_collision_raises_before_load(self, tmp_path, monkeypatch):
        img = tmp_path / "a.png"
        img.write_bytes(b"stub")
        import plain_sight.server as server_mod
        monkeypatch.setattr(server_mod.engine, "_ensure_loaded", lambda: (_ for _ in ()).throw(RuntimeError("should not load")))
        from fastmcp.exceptions import ToolError
        with pytest.raises(ToolError, match="collides"):
            server_mod.describe_batch(
                image_paths=[str(img)],
                manifest_path=str(tmp_path / "a.txt"),
            )


class TestMcpWriteErrorDistinct:
    """B-06a: OSError on sidecar write is not 'description failed'.

    Would have caught: except Exception mapping ENOSPC to the inference string.
    """

    def test_enospace_is_write_failure(self, tmp_path, monkeypatch):
        img = tmp_path / "a.png"
        img.write_bytes(b"stub")
        import plain_sight.server as server_mod
        monkeypatch.setattr(server_mod.engine, "_ensure_loaded", lambda: None)
        monkeypatch.setattr(server_mod.engine, "describe", lambda *a, **k: "caption")
        server_mod.engine._model = object()  # pretend loaded so _ensure_model skips

        def boom(path, text):
            raise OSError(28, "No space left on device")

        monkeypatch.setattr("plain_sight.server.write_sidecar_atomic", boom)
        result = server_mod.describe_batch(image_paths=[str(img)])
        assert result["errors"] == 1
        msg = result["error_details"][0]["error"]
        assert "write" in msg.lower() or "disk" in msg.lower() or "IO" in msg
        assert msg != "description failed"


class TestAtomicSidecarWrite:
    """B-02: empty sidecar is recaptioned; replace is used; interrupt copy updated.

    Would have caught: exists()-only skip of a 0-byte file, and write_text
    truncating the destination in place.
    """

    def test_empty_sidecar_is_recaptioned(self, tmp_path, monkeypatch):
        img = tmp_path / "a.png"
        img.write_bytes(b"stub")
        empty = tmp_path / "a.txt"
        empty.write_text("", encoding="utf-8")
        monkeypatch.setattr(
            "plain_sight.cli.Florence2Engine.describe",
            lambda self, *a, **k: "new caption",
        )
        code = main(["batch", str(img)])
        assert code == 0
        assert empty.read_text(encoding="utf-8") == "new caption"

    def test_nonempty_sidecar_still_skipped(self, tmp_path, monkeypatch):
        img = tmp_path / "a.png"
        img.write_bytes(b"stub")
        (tmp_path / "a.txt").write_text("old", encoding="utf-8")
        monkeypatch.setattr(
            "plain_sight.cli.Florence2Engine.describe",
            lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("should skip")),
        )
        code = main(["batch", str(img)])
        assert code == 0
        assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "old"

    def test_replace_is_used(self, tmp_path, monkeypatch):
        dest = tmp_path / "a.txt"
        seen = {}

        real_replace = os.replace

        def spy(src, dst):
            seen["src"] = str(src)
            seen["dst"] = str(dst)
            return real_replace(src, dst)

        monkeypatch.setattr("plain_sight.sidecars.os.replace", spy)
        write_sidecar_atomic(dest, "hello")
        assert dest.read_text(encoding="utf-8") == "hello"
        assert seen["dst"] == str(dest)
        assert seen["src"].endswith(".tmp")
        assert not dest.with_name("a.txt.tmp").exists()

    def test_interrupt_hint_names_discard(self):
        assert "in-flight sidecar discarded" in open(
            "src/plain_sight/cli.py", encoding="utf-8"
        ).read()


class TestVramDeviceScoped:
    """B-04: cpu engines must not report a current-device CUDA number.

    Full cuda:N scoping needs a GPU; this catches the unscoped
    memory_allocated() call on the default device.
    """

    def test_cpu_status_omits_vram(self, cold_engine):
        status = cold_engine.status()
        assert "vram_mb" not in status


class TestVerifyShMarker:
    """B-06b: verify.sh must use the same marker CI does.

    Would have caught: Wave 1 leaving verify.sh on a hardcoded filename.
    """

    def test_verify_sh_uses_not_dogfood_marker(self):
        text = open("verify.sh", encoding="utf-8").read()
        assert '-m "not dogfood"' in text
        step3 = text.split("== 3/4")[1]
        assert "tests/test_edge_cases.py" not in step3
        assert "PYTEST_DEBUG_TEMPROOT" in step3
        pytest_lines = [
            line for line in step3.splitlines()
            if "pytest" in line and not line.strip().startswith("#")
        ]
        assert pytest_lines and all("--basetemp" not in line for line in pytest_lines)
        gitignore = open(".gitignore", encoding="utf-8").read()
        assert ".pytest-temproot/" in gitignore


class TestErrAsciiSeparator:
    """B-05: _err separator is ASCII. Would have caught the em-dash in the format.

    Mojibake on a real cp1252 pipe is hardware/codepage; this catches the glyph.
    """

    def test_separator_is_ascii_double_dash(self, capsys):
        _err("CODE", "message", "hint")
        line = capsys.readouterr().err
        assert " — " not in line
        assert " -- " in line
        assert line.encode("ascii")  # must not raise

    def test_unknown_detail_message_is_ascii(self):
        with pytest.raises(ValueError) as exc:
            Florence2Engine._validate_detail("ultra")
        str(exc.value).encode("ascii")


class TestStageCHelp:
    """C-04, C-07, C-09: CLI contract is in --help, ASCII, every flag has help.

    Byte-level ASCII would have caught C-07. Walking parser actions would
    have caught C-09 (batch --detail with empty help).
    """

    def test_top_level_help_is_ascii_and_has_epilog(self):
        text = build_parser().format_help()
        text.encode("ascii")
        assert "Exit codes" in text
        assert "stderr" in text
        assert "stdout" in text

    def test_batch_help_mentions_skip_and_hours(self):
        sub = build_parser()._subparsers._group_actions[0].choices["batch"]
        text = sub.format_help()
        text.encode("ascii")
        assert "--overwrite" in text
        assert "hours" in text.lower() or "skipped" in text.lower()

    def test_every_flag_has_help(self):
        parser = build_parser()
        sub = parser._subparsers._group_actions[0]
        for name, sp in sub.choices.items():
            for action in sp._actions:
                if action.option_strings and action.option_strings != ["-h", "--help"]:
                    assert action.help, f"{name} {action.option_strings} has no help"
                    action.help.encode("ascii")

    def test_missing_command_points_at_help(self, capsys):
        with pytest.raises(SystemExit) as exc:
            build_parser().parse_args([])
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "--help" in err
        assert "describe" in err


class TestStageCLoadAnnouncement:
    """C-01 + C-05: default-verbosity stderr before first describe.

    Would have caught: 11s of silence, and the stall after 800 skipped files.
    """

    def test_describe_announces_before_loader(self, tmp_path, monkeypatch, capsys):
        img = tmp_path / "a.png"
        img.write_bytes(b"stub")
        order = []

        def fake_describe(self, *a, **k):
            order.append("describe")
            return "caption"

        monkeypatch.setattr("plain_sight.cli.Florence2Engine.describe", fake_describe)
        monkeypatch.setattr(
            "plain_sight.cli.Florence2Engine._ensure_loaded",
            lambda self: order.append("load"),
        )
        code = main(["describe", str(img)])
        err = capsys.readouterr().err
        assert code == 0
        assert "loading" in err.lower()
        assert "1.5 GB" in err
        assert order[0] == "describe"

    def test_batch_announces_before_skips_finish(self, tmp_path, monkeypatch, capsys):
        skip_img = tmp_path / "a.png"
        work_img = tmp_path / "b.png"
        skip_img.write_bytes(b"stub")
        work_img.write_bytes(b"stub")
        (tmp_path / "a.txt").write_text("old", encoding="utf-8")
        calls = []

        def fake_describe(self, image_path, detail="high", max_new_tokens=None):
            calls.append(image_path)
            return "caption"

        monkeypatch.setattr("plain_sight.cli.Florence2Engine.describe", fake_describe)
        code = main(["batch", str(tmp_path)])
        err = capsys.readouterr().err
        assert code == 0
        assert "loading" in err.lower()
        assert err.lower().index("loading") < err.find("[") if "[" in err else True
        assert len(calls) == 1
        assert "skip (exists)" not in err
        assert "[heartbeat]" in err


class TestStageCDryRun:
    """C-03: --dry-run loads nothing, writes nothing; collisions still exit 1."""

    def test_dry_run_writes_nothing(self, tmp_path, monkeypatch, capsys):
        img = tmp_path / "a.png"
        img.write_bytes(b"stub")
        monkeypatch.setattr(
            "plain_sight.cli.Florence2Engine.describe",
            lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("no load")),
        )
        monkeypatch.setattr(
            "plain_sight.cli.Florence2Engine._ensure_loaded",
            lambda self: (_ for _ in ()).throw(RuntimeError("no load")),
        )
        code = main(["batch", str(img), "--dry-run"])
        out = capsys.readouterr().out
        assert code == 0
        payload = json.loads(out)
        assert payload["dry_run"] is True
        assert payload["would_write"] == 1
        assert payload["would_skip"] == 0
        assert list(tmp_path.glob("*.txt")) == []

    def test_dry_run_collision_still_exits_1(self, tmp_path, capsys):
        (tmp_path / "img.png").write_bytes(b"stub")
        (tmp_path / "img.jpg").write_bytes(b"stub")
        code = main(["batch", str(tmp_path), "--dry-run"])
        err = capsys.readouterr().err
        assert code == 1
        assert "SIDECAR_COLLISION" in err
        assert list(tmp_path.glob("*.txt")) == []


class TestStageCMcpBatchDuration:
    """C-06: describe_batch's description discloses the wait."""

    def test_describe_batch_doc_mentions_duration(self):
        import plain_sight.server as server_mod
        doc = server_mod.describe_batch.__doc__
        assert "1-2" in doc or "1–2" in doc
        assert "overwrite" in doc.lower()


class TestP903TestsImportable:
    """P9-03: tests package must import under the pytest console script.

    Would have caught: no pythonpath, so `from tests.conftest import` dies
    in CI while `python -m pytest` stays green.
    """

    def test_make_text_image_importable(self, tmp_path):
        from tests.conftest import make_text_image
        path = make_text_image(tmp_path / "t.png", "HELLO")
        assert Path(path).is_file()


class TestP901OcrCaveat:
    """P9-01: OCR never presents output as verified extracted text.

    CI-safe: the envelope is the gate. GPU tests live in test_dogfood.py.
    Reverting absence_of_text_unreliable would fail this.
    """

    def test_json_ocr_qualifies_unconditionally(self, tmp_path, monkeypatch, capsys):
        img = tmp_path / "a.png"
        img.write_bytes(b"stub")
        monkeypatch.setattr("plain_sight.cli.Florence2Engine.ocr", lambda self, *a, **k: "2")
        monkeypatch.setattr("plain_sight.cli.Florence2Engine._ensure_loaded", lambda self: None)
        code = main(["ocr", str(img), "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert code == 0
        assert payload["text"] == "2"
        assert payload["absence_of_text_unreliable"] is True
        assert payload["note"] == OCR_ABSENCE_NOTE

    def test_plain_ocr_prints_caveat_on_stderr(self, tmp_path, monkeypatch, capsys):
        img = tmp_path / "a.png"
        img.write_bytes(b"stub")
        monkeypatch.setattr("plain_sight.cli.Florence2Engine.ocr", lambda self, *a, **k: "-")
        monkeypatch.setattr("plain_sight.cli.Florence2Engine._ensure_loaded", lambda self: None)
        code = main(["ocr", str(img)])
        captured = capsys.readouterr()
        assert code == 0
        assert captured.out.strip() == "-"
        assert "OCR_CAVEAT" in captured.err


class TestP902RevisionOnPayloads:
    """P9-02: every structured model-output payload names revision_resolved.

    Would have caught: stamping status() but not describe/ocr JSON.
    Remove the key from one surface and this fails.
    """

    def test_cli_and_mcp_payloads_include_revision(self, tmp_path, monkeypatch, capsys):
        img = tmp_path / "a.png"
        img.write_bytes(b"stub")

        # Stub the model-dependent dependency, NOT output_provenance itself --
        # the real output_provenance must run or this gate cannot see its keys.
        monkeypatch.setattr(Florence2Engine, "resolved_revision", lambda self: "abc123")
        monkeypatch.setattr(Florence2Engine, "describe", lambda self, *a, **k: "caption")
        monkeypatch.setattr(Florence2Engine, "ocr", lambda self, *a, **k: "2")
        monkeypatch.setattr(Florence2Engine, "_ensure_loaded", lambda self: None)

        main(["describe", str(img), "--json"])
        desc = json.loads(capsys.readouterr().out)
        assert desc["revision_resolved"] == "abc123"

        main(["ocr", str(img), "--json"])
        ocr = json.loads(capsys.readouterr().out)
        assert ocr["revision_resolved"] == "abc123"

        main(["batch", str(img)])
        batch = json.loads(capsys.readouterr().out)
        assert batch["revision_resolved"] == "abc123"

        import plain_sight.server as server_mod

        # Patched separately: earlier tests importlib.reload plain_sight.engine
        # and plain_sight.server, so type(server_mod.engine) is not always the
        # same class object as the Florence2Engine imported at module top.
        monkeypatch.setattr(
            type(server_mod.engine), "resolved_revision", lambda self: "abc123"
        )
        monkeypatch.setattr(server_mod.engine, "_ensure_loaded", lambda: None)
        monkeypatch.setattr(server_mod.engine, "describe", lambda *a, **k: "caption")
        monkeypatch.setattr(server_mod.engine, "ocr", lambda *a, **k: "2")

        d = server_mod.describe_image(str(img))
        assert d["revision_resolved"] == "abc123"
        r = server_mod.read_text(str(img))
        assert r["revision_resolved"] == "abc123"
        b = server_mod.describe_batch(image_paths=[str(img)], write_sidecars=False)
        assert b["revision_resolved"] == "abc123"
