---
title: Reference
description: Exact MCP tool parameters and returns, CLI flags, detail tiers, and exit codes.
sidebar:
  order: 4
---

## Detail tiers

| Tier | Florence-2 task token | Output |
|------|----------------------|--------|
| `low` | `<CAPTION>` | one short sentence |
| `medium` | `<DETAILED_CAPTION>` | a few sentences |
| `high` (default) | `<MORE_DETAILED_CAPTION>` | a full paragraph |
| — (`ocr` / `read_text`) | `<OCR>` | the visible text |

`high` is a paragraph, not an essay — Florence-2 is a compact 0.77B model whose
edge is throughput and license, not art-critic depth. If a caption looks
truncated, raise `max_new_tokens` (default 1024, ceiling 4096).

## MCP tools

### describe_image

```
describe_image(image_path, detail="high", max_new_tokens=None)
```

Returns `{description, detail, task, model_id, image_path, elapsed_ms}`.

### describe_batch

```
describe_batch(image_paths[], detail="high", prefix="", suffix="",
               write_sidecars=True, out_dir=None, overwrite=False,
               max_new_tokens=None)
```

Max 100 images per call. With `write_sidecars` (default) each caption lands in
`<image-stem>.txt` — exact basename pairing, `prefix + caption + suffix` bare
concatenation. Existing sidecars are skipped unless `overwrite=true`, and
skipped items cost no inference. With `write_sidecars=false` the captions come
back inline instead.

Returns `{total, described, skipped_existing, errors, detail, write_sidecars,
out_dir, results[], error_details?, elapsed_ms}` — per-item failures never
abort the batch.

### read_text

```
read_text(image_path, max_new_tokens=None)
```

Florence-2 `<OCR>`. Returns `{text, model_id, image_path, elapsed_ms}`.

### sight_status

Engine info — model id, device, dtype, loaded state, versions, VRAM when
loaded — plus honesty guidance. Never triggers a model load.

### sight_selftest

Describes the bundled reference images and checks the outputs are sane
(non-trivial length, on-subject keywords, tier ordering). Loads the model.
Returns `{passed, checks[], model_id, device, torch_version,
transformers_version, elapsed_ms}`.

## CLI

```
plain-sight describe <image> [--detail low|medium|high] [--max-new-tokens N] [--json]
plain-sight ocr <image> [--max-new-tokens N] [--json]
plain-sight batch <paths...> [--detail ...] [--prefix S] [--suffix S]
                             [--out-dir D] [--overwrite] [--max-new-tokens N]
plain-sight status
plain-sight selftest
plain-sight --version
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | ok |
| 1 | user error — bad path, invalid input, bad usage, empty batch, batch where every item failed |
| 2 | runtime error — internal failure, failing selftest |
| 3 | partial success — batch where some items failed and some wrote |

Errors print one structured line to stderr:
`plain-sight: [CODE] message — hint`.

## Python API

The engine imports without any MCP dependency:

```python
from plain_sight.engine import Florence2Engine
from plain_sight.sidecars import compose_caption, sidecar_path_for

e = Florence2Engine()
caption = e.describe("hero.png", detail="high")
text = e.ocr("screenshot.png")
```

`plain_sight.sidecars` carries the pure-stdlib caption contract
(`compose_caption`, `sidecar_path_for`, `iter_image_files`) — testable and
usable without torch.
