---
title: Configuration
description: Every environment variable, device and precision guidance, and the model-pinning story.
sidebar:
  order: 3
---

All configuration is environment variables — nothing is written to config files.

## Environment variables

| Variable | Default | What it does |
|----------|---------|--------------|
| `PLAIN_SIGHT_MODEL_ID` | `florence-community/Florence-2-large` | HuggingFace model to load |
| `PLAIN_SIGHT_MODEL_REVISION` | `4271c66b…` (**pinned**) | Model revision; the mechanism behind the reproducibility claim |
| `PLAIN_SIGHT_MODEL_DIR` | HF default cache | Explicit HuggingFace hub directory |
| `PLAIN_SIGHT_DEVICE` | `cuda` if available, else `cpu` | torch device |
| `PLAIN_SIGHT_DTYPE` | `float16` on CUDA, full precision on CPU | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | Default generation cap (per-call override up to 4096) |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | Beam width for deterministic decoding |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` — stderr only, both surfaces |
| `PLAIN_SIGHT_EAGER_LOAD` | unset | Truthy → load the model at server start instead of first call |

## Eager loading

With `PLAIN_SIGHT_EAGER_LOAD` truthy the MCP server loads at start rather than
on first tool call. A failure there **does not kill the server** — the import
always succeeds, `sight_status` reports `eager_load_attempted` and
`eager_load_error`, and the first tool call that needs the model raises a
`ToolError` carrying the stored cause. `sight_status` never triggers a load in
any configuration.

## Device and precision

The defaults are right for most machines: CUDA + `float16` needs ~1.5–2 GB VRAM
and runs a high-detail caption in ~1 s. Force full precision with
`PLAIN_SIGHT_DTYPE=float32` if you see numeric issues; drop to CPU with
`PLAIN_SIGHT_DEVICE=cpu` (about 10× slower, still correct).

Out-of-memory errors come back with this exact advice in the message —
`float16` first, then `cpu`.

`status` reports `vram_mb` scoped to the configured device, and omits the field
entirely on CPU rather than reporting a number that means nothing.

## Model cache

The model resolves through the standard HuggingFace cache (`HF_HOME` /
`HF_HUB_CACHE`). `PLAIN_SIGHT_MODEL_DIR` points at a hub directory explicitly —
useful when weights live on a dedicated drive:

```json
"env": {
  "HF_HOME": "E:/AI-Models/hf-cache",
  "PLAIN_SIGHT_MODEL_DIR": "E:/AI-Models/hf-cache/hub"
}
```

## Why this model pin

`PLAIN_SIGHT_MODEL_ID` defaults to **`florence-community/Florence-2-large`** —
the official native-transformers conversion of Microsoft's MIT-licensed
Florence-2 release. Two things worth knowing:

- **The `microsoft/Florence-2-*` originals will not load here.** They ship
  pre-native configs that require `trust_remote_code=True` — executing Python
  fetched from the hub — which this tool refuses on principle. The community
  conversion is the same weights (MIT, license tag verified) with native
  configs.
- **The Florence-2 fine-tune zoo is deliberately not offered.** MiaoshouAI
  PromptGen, CogFlorence, the SD3/Flux captioners, Castollux — their licenses
  and load paths vary. Overriding `PLAIN_SIGHT_MODEL_ID` to one of them is
  possible, but the license question is then yours.

## Determinism, and what it is relative to

Decoding is `do_sample=false` + beam search (`PLAIN_SIGHT_NUM_BEAMS`, default 3).
The same image at the same tier reproduces the same caption byte-for-byte, which
is what makes caption diffs in a dataset meaningful. There is no seed knob
because none is needed when sampling is off.

**That guarantee is relative to a set of weights, so the revision is pinned by
default.** Without a pin, HuggingFace resolves to whatever the repository's
default branch points at, and a silent retag would change captions under
unchanged inputs — determinism within a run, drift across months. The pin is
what makes the claim survive time.

So that the guarantee is checkable rather than asserted, **every payload
carrying model output also carries the resolved revision** — the value the
loaded model actually reports, not the constant that was requested:

- `describe_image`, `read_text`, `describe_batch`, `sight_selftest`
- the CLI's `--json` modes and the `batch` summary
- `sight_status` reports requested and resolved separately, so a mismatch is
  visible rather than silent

For a whole run, `--manifest PATH` records versions, model, both revisions,
device, dtype, tier, prefix/suffix and per-image results in one JSON file.
