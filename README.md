<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/plain-sight/readme.png" alt="plain-sight — an AI says what it sees" width="400">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/plain-sight/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/plain-sight/"><img src="https://img.shields.io/badge/landing-page-22d3ee.svg" alt="Landing Page"></a>
</p>

**Version:** 1.1.0

**An AI says what it sees.** Generative image describer — MCP server + CLI wrapping
Florence-2 (MIT) for prose descriptions, OCR, and LoRA-dataset caption sidecars.
Runs locally, deterministic against a pinned model revision.

The sibling of [ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp):

| | ai-eyes-mcp | plain-sight |
|---|---|---|
| Job | **judges** images | **describes** images |
| Model | SigLIP2 (discriminative) | Florence-2 (generative) |
| Output | calibrated scores | prose / OCR / caption files |
| Failure mode | can't narrate | can hallucinate detail |
| Reach for it when | "does this image contain X?" | "what is in this image?" |

## Honesty contract

Descriptions are **generative**: fluent, usually accurate, and capable of inventing
detail. plain-sight makes output *reproducible* — deterministic decoding against a
pinned model revision, so the same image yields the same caption — **not**
*guaranteed true*. For verifying a specific claim about an image, use
ai-eyes-mcp's `image_verify`; it measures, it doesn't narrate. The two tools are
different model families by design, so one can check the other.

Three specific limits, stated because they are easy to discover the hard way:

- **OCR cannot report the absence of text.** Florence-2 emits a decoded string for
  every image, including images containing no text at all — a photograph may
  return `'2'`. That output is lexically indistinguishable from a correct reading
  of a numeral. Every OCR result therefore carries
  `absence_of_text_unreliable: true` (MCP) or a `[OCR_CAVEAT]` line on stderr
  (CLI). plain-sight never suppresses or empties the result, because a short
  reading may be genuine — it tells you the signal does not exist.
- **Captions describe; they do not verify.** A confident sentence about an image
  is not evidence the thing described is present.
- **Reproducibility is per-revision.** Pinning is what makes the determinism claim
  meaningful across time; see [Provenance](#provenance).

## Tools (MCP)

| Tool | What it does |
|------|-------------|
| `describe_image` | One image → prose description (3 detail tiers) |
| `describe_batch` | N images → `.txt` caption sidecars (the dataset lane) |
| `read_text` | OCR — decode text from an image, with an absence caveat |
| `sight_status` | Health check: model, device, resolved revision, loaded state |
| `sight_selftest` | Describe bundled reference images, sanity-check output |

Every payload that carries model output also carries `model_id` and
`revision_resolved` — see [Provenance](#provenance).

## Quick Start

```bash
pip install -e .
plain-sight-mcp   # starts the STDIO MCP server
```

Or run as a module: `python -m plain_sight`

### CLI

```bash
# One image, full paragraph
plain-sight describe hero.png

# One short sentence
plain-sight describe hero.png --detail low

# OCR (the absence caveat goes to stderr; the text goes to stdout)
plain-sight ocr screenshot.png

# See the plan before writing anything — no model load, no files
plain-sight batch ./dataset --prefix "mcpt_style, " --dry-run

# The dataset lane: caption a directory into .txt sidecars with a trigger token
plain-sight batch ./dataset --prefix "mcpt_style, " --detail high

# Record provenance for the run alongside it
plain-sight batch ./dataset --prefix "mcpt_style, " --manifest ./dataset-run.json

# Re-runs are idempotent — existing sidecars are skipped unless you --overwrite
plain-sight batch ./dataset --prefix "mcpt_style, " --overwrite
```

`batch` flags: `--detail` · `--prefix` · `--suffix` · `--out-dir` · `--overwrite`
· `--max-new-tokens` · `--manifest` · `--dry-run`. Run `plain-sight batch --help`
for the full text; `plain-sight --help` documents exit codes and which stream
carries what.

### What a long run looks like

Progress goes to **stderr**; results go to **stdout**, so
`plain-sight describe x.png > caption.txt` works.

```
plain-sight: loading florence-community/Florence-2-large rev=4271c66b…  caption=4820 skip=0
  (first caption includes model load, ~10s; first-ever run downloads ~1.5 GB)
[1/4820] wrote img_0001.txt
[heartbeat] 1840/4820 written=1801 skipped=32 failed=7  1.4 img/s  ETA 35m
```

The load is announced **before** work begins, with the count of images that will
actually be captioned, so a pause never appears mid-run. Skipped images are
counted on the heartbeat rather than printed one line each — a re-run over a
finished set is quiet. Failures stay one line each.

### Claude Code config

```json
{
  "mcpServers": {
    "plain-sight": {
      "command": "plain-sight-mcp",
      "env": {
        "PLAIN_SIGHT_MODEL_DIR": "/path/to/model/cache"
      }
    }
  }
}
```

## The caption contract (dataset lane)

Built for LoRA training sets (style-dataset-lab and friends):

- **Exact basename pairing:** `img_0042.png` → `img_0042.txt`. No counter
  suffix — unlike ComfyUI's SaveText node, which appends `_00001`.
- **Bare concatenation:** the sidecar contains `prefix + caption + suffix`
  with no delimiter injected. Want `"mcpt_style, <caption>"`? Put the
  comma-space in the prefix.
- **Colliding stems are refused, never merged.** Two images whose stems match —
  `img.png` and `img.jpg` in one folder, or same-stem files from two folders
  under one `--out-dir` — would claim a single `.txt`. plain-sight refuses the
  whole batch before loading the model, names the offenders, and exits `1`.
  It will not rename a sidecar to dodge the clash: trainers pair by exact stem,
  so a rename would orphan the caption and leave the image uncaptioned.
- **Writes are atomic.** Each sidecar is written to a temp file in the same
  directory and moved into place, so an interrupt never leaves a partial caption
  at the final path. A sidecar that exists but is empty is treated as unfinished
  and re-captioned.
- **Idempotent re-runs:** existing non-empty sidecars are skipped, and cost
  nothing, unless `--overwrite` / `overwrite=true`.
- **Deterministic:** `do_sample=false` + beam search against a pinned revision —
  re-captioning an unchanged image reproduces the same text, so diffs mean
  something.

## Provenance

The dataset lane produces training data. Six months on, the question is which
weights produced which captions — so the answer travels with the output.

- **The model revision is pinned** by default to
  `4271c66b88cdbc05735372ec13b2360108de5317`. Without a pin, HuggingFace resolves
  to whatever the repository's default branch currently points at, and a silent
  retag would change captions under unchanged inputs. Override with
  `PLAIN_SIGHT_MODEL_REVISION`.
- **Every output payload names the weights.** `describe_image`, `read_text`,
  `describe_batch`, `sight_selftest`, and the CLI's `--json` modes and batch
  summary all carry `model_id` and `revision_resolved` — the revision the loaded
  model actually reports, not the constant that was requested. `sight_status`
  reports both, so a mismatch is visible.
- **`--manifest PATH` writes a run record** — tool version, model id, requested
  and resolved revision, device, dtype, detail tier, prefix/suffix, per-image
  results and counts. Opt-in and never inferred: no manifest is written unless
  you pass a path, and a path that collides with a computed sidecar is refused.
  It contains a timestamp, so unlike the captions it is not byte-reproducible.

## Detail tiers

Florence-2's native task ladder:

| Tier | Task token | Output |
|------|-----------|--------|
| `low` | `<CAPTION>` | one short sentence |
| `medium` | `<DETAILED_CAPTION>` | a few sentences |
| `high` (default) | `<MORE_DETAILED_CAPTION>` | a full paragraph |

`high` is a paragraph, not an essay — Florence-2 is a compact (0.77B) model.
Its edge is throughput and license, not art-critic depth. If a caption looks
truncated, raise `max_new_tokens` (default 1024, max 4096).

## Configuration

| Env Var | Default | Purpose |
|---------|---------|---------|
| `PLAIN_SIGHT_MODEL_ID` | `florence-community/Florence-2-large` | HuggingFace model |
| `PLAIN_SIGHT_MODEL_REVISION` | `4271c66b…` (pinned) | Model revision; the mechanism behind the reproducibility claim |
| `PLAIN_SIGHT_MODEL_DIR` | HF default cache | Model cache directory |
| `PLAIN_SIGHT_DEVICE` | `auto` (cuda if available, else cpu) | torch device |
| `PLAIN_SIGHT_DTYPE` | `float16` on CUDA, full precision on CPU | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | Default generation cap |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | Beam width (deterministic decoding) |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PLAIN_SIGHT_EAGER_LOAD` | unset | If truthy, load the model at server start |

**Logging:** stderr only (stdout is the MCP protocol channel), logger name
`plain_sight`. `PLAIN_SIGHT_LOG_LEVEL` is honoured on both surfaces.

**Eager load:** with `PLAIN_SIGHT_EAGER_LOAD` truthy, the MCP server loads at
start rather than on first call. A failure there never kills the server import —
it is reported by `sight_status` as `eager_load_error` and raised as a `ToolError`
on the first tool call that needs the model.

**First call:** the model loads lazily by default — the first describe/OCR call
loads Florence-2 (~10–20s on GPU; the first-ever call downloads ~1.5 GB).
Subsequent calls are ~1–2s per image at `high` detail on a modern GPU.

## License posture

- **This tool:** MIT.
- **The model:** pinned to `florence-community/Florence-2-large` — the
  official native-transformers conversion of Microsoft's Florence-2 release.
  **MIT** (hub license tag verified 2026-08-19). Commercial use clean.
- **Why not `microsoft/Florence-2-large`?** Same weights, same MIT license,
  but the original repos ship pre-native configs that only load via
  `trust_remote_code` — which this tool refuses on principle. The community
  conversion loads with transformers' built-in Florence-2 classes.
- **Deliberately not offered:** the Florence-2 fine-tune zoo (MiaoshouAI
  PromptGen, CogFlorence, SD3/Flux captioners, Castollux). Their licenses are
  unverified; they stay out until cleared. Overriding `PLAIN_SIGHT_MODEL_ID`
  to one of them is possible but puts the license question on you.
- **No remote code:** the engine uses transformers' *native* Florence-2
  support only — `trust_remote_code` is never passed, so no hub-fetched
  Python ever executes. This requires `transformers >= 4.51`.

## Security and Trust

This tool operates **locally only**.

- **Data touched:** local image files (read-only); the HuggingFace model cache
  (written once on first download); and the files it writes — `.txt` caption
  sidecars, only where the caller asked (`out_dir` or next to the image), plus
  one JSON manifest if and only if `--manifest` / `manifest_path` supplies an
  explicit path. Existing sidecars are replaced only under explicit
  `--overwrite`.
- **No network egress at runtime** — the model downloads once on first use,
  then all inference is local.
- **No remote code execution** — native transformers classes only;
  `trust_remote_code` is never passed, so no hub-fetched Python ever executes.
- **No secrets handling, no telemetry** — nothing is read from or sent anywhere.
- **Structured errors only** — raw stack traces never reach MCP clients or
  CLI users. CLI exit codes: 0 ok · 1 user error · 2 runtime error ·
  3 partial success.

Full policy: [SECURITY.md](SECURITY.md). Actively maintained; supported
versions listed there.

## Requirements

- Python >= 3.10
- `transformers >= 4.51` (native Florence-2)
- CUDA GPU recommended (~2 GB VRAM at FP16); CPU fallback works (slower)
- Model downloads ~1.5 GB on first use

## Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# CI-safe suite (no model, no GPU) — this is what CI runs
pytest -m "not dogfood" -v

# Dogfood suite (real model + GPU, local only)
pytest -m dogfood -v

# Everything
pytest

# Full verify: imports, MCP tool surface, CI-safe tests, wheel + sdist build
bash verify.sh
```

Tests select by marker, not by filename, so a new CI-safe test file is picked up
without touching CI. On Windows, a stale reparse point in the shared system temp
can break pytest's default temp root; `verify.sh` relocates it via
`PYTEST_DEBUG_TEMPROOT`, and `pythonpath = ["."]` keeps the console script and
`python -m pytest` in agreement.

## Architecture

```
engine.py    Standalone Florence-2 wrapper — no MCP dependency.
             Lazy-loads the model; validation runs BEFORE the load.
             Owns the provenance stamp and the shared logging setup.
             Importable directly: from plain_sight.engine import Florence2Engine

sidecars.py  The training-data contract, pure stdlib: basename pairing,
             bare concatenation, collision detection, atomic writes,
             directory expansion. Testable without torch.

server.py    FastMCP wrapper exposing engine methods as MCP tools.
             Thin layer: validation, error shaping, tool metadata.

cli.py       argparse CLI over the same engine (describe / ocr / batch /
             status / selftest). Structured errors, meaningful exit codes.
```

The architecture is borrowed deliberately from
[ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp) — same
engine/server split, same error shaping, same selftest pattern. A cloud
sibling of the same contract runs on Comfy Cloud as the
`caption-florence2-v1` workflow (one-image-per-job metadata rider; this tool
is the bulk lane).

## License

MIT

---

Built by [MCP Tool Shop](https://mcp-tool-shop.github.io/)
