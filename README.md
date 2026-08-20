# plain-sight

**Version:** 1.0.0

**An AI says what it sees.** Generative image describer — MCP server + CLI wrapping
Florence-2 (MIT) for prose descriptions, OCR, and LoRA-dataset caption sidecars.
Runs locally, deterministic by default.

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
detail. plain-sight makes output *reproducible* (deterministic decoding — the same
image yields the same caption), not *guaranteed true*. For verifying a specific
claim about an image, use ai-eyes-mcp's `image_verify` — it measures, it doesn't
narrate. The two tools are different model families by design, so one can check
the other.

## Tools (MCP)

| Tool | What it does |
|------|-------------|
| `describe_image` | One image → prose description (3 detail tiers) |
| `describe_batch` | N images → `.txt` caption sidecars (the dataset lane) |
| `read_text` | OCR — extract visible text from an image |
| `sight_status` | Health check: model, device, loaded state |
| `sight_selftest` | Describe bundled reference images, sanity-check output |

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

# OCR
plain-sight ocr screenshot.png

# The dataset lane: caption a directory into .txt sidecars with a trigger token
plain-sight batch ./dataset --prefix "mcpt_style, " --detail high

# Re-runs are idempotent — existing sidecars are skipped unless you --overwrite
plain-sight batch ./dataset --prefix "mcpt_style, " --overwrite
```

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
- **Idempotent re-runs:** existing sidecars are skipped (and cost nothing)
  unless `--overwrite` / `overwrite=true`.
- **Deterministic:** `do_sample=false` + beam search — re-captioning an
  unchanged image reproduces the same text, so diffs mean something.

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
| `PLAIN_SIGHT_MODEL_DIR` | HF default cache | Model cache directory |
| `PLAIN_SIGHT_DEVICE` | `auto` (cuda if available, else cpu) | torch device |
| `PLAIN_SIGHT_DTYPE` | `float16` on CUDA, full precision on CPU | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | Default generation cap |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | Beam width (deterministic decoding) |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `PLAIN_SIGHT_EAGER_LOAD` | unset | If truthy, load the model at server start |

**Logging:** stderr only (stdout is the MCP protocol channel), logger name
`plain_sight`.

**First call:** the model loads lazily — the first describe/OCR call loads
Florence-2 (~10–20s on GPU; the first-ever call downloads ~1.5 GB). Subsequent
calls are ~1–2s per image at `high` detail on a modern GPU.

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
  (written once on first download); `.txt` caption sidecars — the ONLY files
  it writes, only where the caller asked (`out_dir` or next to the image),
  and existing sidecars are only replaced under explicit `--overwrite`.
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

# CI-safe tests (no model, no GPU)
pytest tests/test_edge_cases.py -v

# Dogfood tests (real model + GPU)
pytest tests/test_dogfood.py -v

# Full verify: imports, edge tests, build
bash verify.sh
```

## Architecture

```
engine.py    Standalone Florence-2 wrapper — no MCP dependency.
             Lazy-loads the model; validation runs BEFORE the load.
             Importable directly: from plain_sight.engine import Florence2Engine

sidecars.py  The training-data contract, pure stdlib: basename pairing,
             bare concatenation, directory expansion. Testable without torch.

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
