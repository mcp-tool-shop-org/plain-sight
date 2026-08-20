---
title: Usage
description: The CLI commands, the MCP tools, and the LoRA dataset-captioning lane.
sidebar:
  order: 2
---

## CLI

Five commands, one engine. Exit codes follow the toolshop canon:
**0** ok · **1** user error (bad input or usage) · **2** runtime error ·
**3** partial success. `plain-sight --help` states them, along with which
stream carries what and the first-load cost.

Progress goes to **stderr**, results to **stdout**, so
`plain-sight describe x.png > caption.txt` works.

### describe

```bash
plain-sight describe hero.png --detail high
plain-sight describe hero.png --detail low --json
plain-sight describe hero.png --max-new-tokens 2048
```

Prints the description to stdout (pipe-friendly). `--json` wraps it with the
tier, task token, model id, and resolved revision. Raise `--max-new-tokens`
(default 1024, max 4096) if a high-detail paragraph looks truncated.

The first call loads the model. plain-sight says so before it starts, at
default verbosity, rather than sitting silent for ten seconds.

### ocr

```bash
plain-sight ocr screenshot.png
plain-sight ocr document.png --json
```

Runs Florence-2's `<OCR>` task — signage, UI labels, documents.

**It cannot tell you an image has no text.** Florence-2 emits a decoded string
for every image, so a photograph with no writing in it may return `'2'` — output
lexically indistinguishable from a correct reading of a numeral. Every result
therefore carries `absence_of_text_unreliable: true` in JSON, or an
`[OCR_CAVEAT]` line on stderr in plain mode.

plain-sight never empties, suppresses, or length-thresholds that result: a short
reading may be genuine, and substituting an empty string would trade one
unverified claim for another. It tells you the signal does not exist and hands
you the text.

### batch — the dataset lane

```bash
# See the plan before anything happens — no model load, no files written
plain-sight batch ./dataset --dry-run

# Caption every image in a directory into .txt sidecars
plain-sight batch ./dataset --detail high

# LoRA training sets: prepend a trigger token (include your own separator)
plain-sight batch ./dataset --prefix "mcpt_style, "

# Collect sidecars into a separate directory
plain-sight batch ./dataset --out-dir ./captions

# Record provenance for the run alongside it
plain-sight batch ./dataset --manifest ./dataset-run.json

# Re-caption images whose sidecar already exists
plain-sight batch ./dataset --overwrite
```

Flags: `--detail` · `--prefix` · `--suffix` · `--out-dir` · `--overwrite` ·
`--max-new-tokens` · `--manifest` · `--dry-run`.

Accepts files and directories mixed; directories are scanned (non-recursively)
for `png / jpg / jpeg / webp / bmp / gif / tif / tiff`.

**What a long run looks like.** A dataset run is hours, so it reports rate and
ETA rather than only scrolling filenames:

```
plain-sight: loading florence-community/Florence-2-large rev=4271c66b…  caption=4820 skip=0
[1/4820] wrote img_0001.txt
[heartbeat] 1840/4820 written=1801 skipped=32 failed=7  1.4 img/s  ETA 35m
```

The load is announced **before** work begins, with the count of images that will
actually be captioned — so the pause never appears mid-run after a stretch of
skips. Skipped images are counted on the heartbeat rather than printed one line
each, so a re-run over a finished set is quiet. Failures stay one line each.

**The caption contract:**

- **Exact basename pairing** — `img_0042.png` → `img_0042.txt`. No counter
  suffix, so sidecars pair with images forever.
- **Bare concatenation** — the file contains `prefix + caption + suffix`
  exactly; no delimiter is injected. Want `"trigger, caption"`? Put the
  comma-space in the prefix.
- **Colliding stems are refused, never merged.** `img.png` and `img.jpg` in one
  folder would both claim `img.txt`. plain-sight refuses the whole batch before
  loading the model, names the offenders, and exits `1`. It will not rename a
  sidecar to dodge the clash — trainers pair by exact stem, so a rename would
  orphan the caption and leave the image uncaptioned.
- **Writes are atomic** — temp file plus rename, so an interrupt never leaves a
  partial caption at the final path. An existing but empty sidecar is treated as
  unfinished and re-captioned.
- **Idempotent re-runs** — existing non-empty sidecars are skipped (and cost
  zero inference) unless `--overwrite`.

### status and selftest

```bash
plain-sight status    # engine info as JSON — does NOT load the model
plain-sight selftest  # describes bundled reference images, checks sanity
```

## MCP tools

| Tool | What it does |
|------|-------------|
| `describe_image(image_path, detail?, max_new_tokens?)` | One image → prose |
| `describe_batch(image_paths[], detail?, prefix?, suffix?, write_sidecars?, out_dir?, overwrite?, max_new_tokens?, manifest_path?)` | Up to 100 images → sidecars (or inline captions with `write_sidecars: false`) |
| `read_text(image_path, max_new_tokens?)` | OCR, with the absence caveat |
| `sight_status()` | Health check — never triggers a model load |
| `sight_selftest()` | Bundled-image sanity proof — loads the model |

Every payload carrying model output also carries `model_id` and
`revision_resolved`.

`describe_batch` **blocks** until every image completes — roughly 1–2 s each
plus ~10–20 s if the model is not yet loaded, so a 100-image call can run for
minutes with no intermediate output. MCP has no progress stream for tool calls.
Chunk large sets; existing sidecars are skipped unless `overwrite=true`, so a
retry after a timeout is cheap.

Errors come back as structured, actionable messages (what broke, what to do),
never stack traces. A batch never fails wholesale on one bad image — per-item
errors land in `error_details` while the rest complete, and a write failure is
reported as a write failure rather than collapsed into "description failed".

## The verification pairing

For dataset work where captions become training signal, spot-check what matters:

1. `describe_batch` writes the captions (this tool — generative).
2. Extract the load-bearing claims (species, objects, weapons…).
3. Verify each claim with ai-eyes-mcp's `image_verify` (SigLIP2 —
   discriminative, different model family, measures instead of narrating).

No model verifies its own output; that's the point of the pair.
