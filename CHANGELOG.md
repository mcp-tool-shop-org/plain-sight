# Changelog

## 1.1.0 — 2026-08-20

Dogfood swarm: health pass (bugs, proactive, humanization) plus a pre-Phase-9
wave. 39 tests → 88. Two CRITICALs closed, both of the same shape — output a
downstream consumer would trust, wrong, with no signal.

### Fixed — the dataset lane could silently mislabel training data

- **Sidecar collisions are refused, not merged.** Sidecar paths derived from the
  image stem alone, so `img.png` and `img.jpg` in one folder both claimed
  `img.txt`. The second was reported as `skip (exists)` and the run exited 0 — a
  green run in which one image carried a description of a different image. It
  needed no flags. Colliding batches are now refused before the model loads,
  naming the offenders. Sidecars are never renamed to dodge a clash: trainers
  pair by exact stem, so a rename would orphan the caption.
- **OCR can no longer present invented text as extracted text.** Florence-2
  emits a decoded string for every image, including images with no text — a
  photograph returns `'2'`, lexically indistinguishable from a correct reading.
  Results now always carry `absence_of_text_unreliable` (MCP) or an
  `[OCR_CAVEAT]` line (CLI). The text is never suppressed, emptied, or
  length-thresholded, because a short reading may be genuine.
- **Sidecar writes are atomic** — temp file plus `os.replace`, so an interrupt
  cannot leave a partial caption at the final path. An existing but empty
  sidecar is treated as unfinished and re-captioned.
- **A mid-batch failure no longer aborts the run.** The batch loop caught only
  `FileNotFoundError`/`ValueError`, so a CUDA OOM killed the job and swallowed
  the JSON summary. It now records the failure and continues; exit 3 on partial.

### Fixed — broken promises

- `PLAIN_SIGHT_MODEL_ID` was documented in nine READMEs and honoured by the MCP
  server, while the CLI silently ignored it. Resolved once, at module scope.
- `PLAIN_SIGHT_LOG_LEVEL` was named in the CLI's own error hint and had no
  effect there — DEBUG was unreachable. Shared `configure_logging()` now serves
  both surfaces.
- `PLAIN_SIGHT_EAGER_LOAD` is honoured on the MCP surface again, and a failure
  during eager load no longer kills the server import: it surfaces via
  `sight_status` and as a `ToolError` on first use.
- The CLI emitted a raw traceback at exit 1 when engine construction failed —
  the construction sat outside the error boundary. Now a structured line, exit 2.

### Added — provenance

- **The model revision is pinned** to `4271c66b88cdbc05735372ec13b2360108de5317`.
  Unpinned, HuggingFace resolves to whatever the default branch points at, so a
  silent retag would change captions under unchanged inputs.
  `PLAIN_SIGHT_MODEL_REVISION` overrides.
- **Every output payload names the weights** — `model_id` and the *resolved*
  revision on `describe_image`, `read_text`, `describe_batch`, `sight_selftest`,
  the CLI `--json` modes and the batch summary. `sight_status` reports requested
  and resolved separately, so a mismatch is visible.
- **`--manifest PATH`** writes an opt-in run record: versions, model, both
  revisions, device, dtype, tier, prefix/suffix, per-image results. Never
  inferred; a path colliding with a sidecar is refused.

### Added — it now says what it is doing

- **The load is announced before work begins**, at default verbosity, with the
  count of images that will actually be captioned — so the pause never appears
  mid-run after a stretch of skips.
- **Progress heartbeat** every 25 items or 30s: written / skipped / failed,
  rate, ETA. Per-skip lines are gone; a re-run over a finished set is quiet.
  Failures stay one line each.
- **`--dry-run`** prints the whole plan — model, revision, counts, collisions —
  loading nothing and writing nothing.
- `--help` carries the exit-code table, the stderr/stdout split, and the
  first-load cost. Every flag on every subcommand has help text.

### Changed

- CI and `verify.sh` select tests by marker (`-m "not dogfood"`) rather than by
  filename, so a new CI-safe test file is covered without touching CI.
- `--help` and CLI error output are ASCII; the em-dash separator mojibaked when
  stderr was a cp1252 pipe on Windows.
- `pythonpath = ["."]` so the console script and `python -m pytest` agree.
- `status()` reports device-scoped VRAM, omitted on CPU.

### Notes

Severities throughout this release were assigned by a cross-family panel of
pinned non-Claude model seats with authorship stripped, not by the authors of
the findings. Several moved in both directions.

## 1.0.0 — 2026-08-20

Shipcheck promotion (v0.x → v1.0.0 per org policy). The describe/OCR/sidecar
contract is unchanged.

- CLI exit codes aligned to the studio canon: 0 ok · 1 user error (bad input
  AND bad usage — argparse's native usage-exit of 2 is overridden) ·
  2 runtime error (internal failure, failing selftest) · 3 partial success
  (batch with some failures).
- CI added: paths-gated ubuntu workflow — imports, MCP tool-surface check,
  CI-safe edge tests, `pip-audit` (advisory).
- SECURITY.md: supported-versions table + response timeline.
- README: "Security and Trust" threat-model section.
- `verify.sh` now builds wheel + sdist (clean-build gate).
- SHIP_GATE.md added; hard gates A–D pass.

## 0.1.0 — 2026-08-19

Initial build.

- `Florence2Engine` — native-transformers Florence-2 wrapper (no
  `trust_remote_code`), lazy load, validation before load, deterministic
  decoding (`do_sample=false`, beam search), fp16 on CUDA by default.
- MCP server (`plain-sight-mcp`): `describe_image`, `describe_batch`
  (sidecar dataset lane), `read_text` (OCR), `sight_status`,
  `sight_selftest`.
- CLI (`plain-sight`): `describe`, `ocr`, `batch`, `status`, `selftest` —
  structured errors, exit codes 0/1/2.
- The caption contract: exact basename pairing (`img.png` → `img.txt`, no
  counter), bare `prefix + caption + suffix` concatenation, idempotent
  re-runs (skip existing sidecars unless `--overwrite`).
- Model pinned to MIT `florence-community/Florence-2-large` (the official
  native-transformers conversion; the `microsoft/` originals need
  `trust_remote_code`, which this tool refuses). The PromptGen / CogFlorence
  fine-tune family deliberately excluded pending license verification.
- Architecture borrowed from ai-eyes-mcp (engine/server split, error
  shaping, bundled-asset selftest). Cloud sibling: the `caption-florence2-v1`
  Comfy Cloud workflow (verified 2026-08-19, 6.73 gpu-sec/caption).
- Tests: CI-safe edge suite (validation, sidecar contract, CLI parsing) +
  dogfood suite (real model, determinism, tier ordering, sidecar E2E).
