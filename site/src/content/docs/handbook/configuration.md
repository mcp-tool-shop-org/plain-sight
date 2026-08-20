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
| `PLAIN_SIGHT_MODEL_REVISION` | unset | Pin a specific model revision (commit hash) |
| `PLAIN_SIGHT_MODEL_DIR` | HF default cache | Explicit HuggingFace hub directory |
| `PLAIN_SIGHT_DEVICE` | `cuda` if available, else `cpu` | torch device |
| `PLAIN_SIGHT_DTYPE` | `float16` on CUDA, full precision on CPU | `float16` / `bfloat16` / `float32` |
| `PLAIN_SIGHT_MAX_NEW_TOKENS` | `1024` | Default generation cap (per-call override up to 4096) |
| `PLAIN_SIGHT_NUM_BEAMS` | `3` | Beam width for deterministic decoding |
| `PLAIN_SIGHT_LOG_LEVEL` | `WARNING` | `DEBUG` / `INFO` / `WARNING` / `ERROR` — stderr only |
| `PLAIN_SIGHT_EAGER_LOAD` | unset | Truthy → load the model at server start, fail fast |

## Device and precision

The defaults are right for most machines: CUDA + `float16` needs ~1.5–2 GB VRAM
and runs a high-detail caption in ~1 s. Force full precision with
`PLAIN_SIGHT_DTYPE=float32` if you see numeric issues; drop to CPU with
`PLAIN_SIGHT_DEVICE=cpu` (about 10× slower, still correct).

Out-of-memory errors come back with this exact advice in the message —
`float16` first, then `cpu`.

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
  possible, but the license question is then yours; pin
  `PLAIN_SIGHT_MODEL_REVISION` if you do.

## Determinism

Decoding is `do_sample=false` + beam search (`PLAIN_SIGHT_NUM_BEAMS`, default 3).
The same image at the same tier reproduces the same caption byte-for-byte —
which is what makes caption diffs in a dataset meaningful. There is no seed knob
because none is needed when sampling is off.
