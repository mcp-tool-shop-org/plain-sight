---
title: Usage
description: The CLI commands, the MCP tools, and the LoRA dataset-captioning lane.
sidebar:
  order: 2
---

## CLI

Five commands, one engine. Exit codes follow the toolshop canon:
**0** ok · **1** user error (bad input or usage) · **2** runtime error ·
**3** partial success.

### describe

```bash
plain-sight describe hero.png --detail high
plain-sight describe hero.png --detail low --json
plain-sight describe hero.png --max-new-tokens 2048
```

Prints the description to stdout (pipe-friendly). `--json` wraps it with the
tier, task token, and model id. Raise `--max-new-tokens` (default 1024, max
4096) if a high-detail paragraph looks truncated.

### ocr

```bash
plain-sight ocr screenshot.png
plain-sight ocr document.png --json
```

Runs Florence-2's `<OCR>` task — signage, UI labels, documents. Like all
generative output it can misread; treat it as low-stakes extraction, not
ground truth.

### batch — the dataset lane

```bash
# Caption every image in a directory into .txt sidecars
plain-sight batch ./dataset --detail high

# LoRA training sets: prepend a trigger token (include your own separator)
plain-sight batch ./dataset --prefix "mcpt_style, "

# Collect sidecars into a separate directory
plain-sight batch ./dataset --out-dir ./captions

# Re-caption images whose sidecar already exists
plain-sight batch ./dataset --overwrite
```

Accepts files and directories mixed; directories are scanned (non-recursively)
for `png / jpg / jpeg / webp / bmp / gif / tif / tiff`. Per-file progress goes
to stderr, a JSON summary to stdout.

**The caption contract:**

- **Exact basename pairing** — `img_0042.png` → `img_0042.txt`. No counter
  suffix, so sidecars pair with images forever.
- **Bare concatenation** — the file contains `prefix + caption + suffix`
  exactly; no delimiter is injected. Want `"trigger, caption"`? Put the
  comma-space in the prefix.
- **Idempotent re-runs** — existing sidecars are skipped (and cost zero
  inference) unless `--overwrite`.

### status and selftest

```bash
plain-sight status    # engine info as JSON — does NOT load the model
plain-sight selftest  # describes bundled reference images, checks sanity
```

## MCP tools

| Tool | What it does |
|------|-------------|
| `describe_image(image_path, detail?, max_new_tokens?)` | One image → prose |
| `describe_batch(image_paths[], detail?, prefix?, suffix?, write_sidecars?, out_dir?, overwrite?, max_new_tokens?)` | Up to 100 images → sidecars (or inline captions with `write_sidecars: false`) |
| `read_text(image_path, max_new_tokens?)` | OCR |
| `sight_status()` | Health check — never triggers a model load |
| `sight_selftest()` | Bundled-image sanity proof — loads the model |

Errors come back as structured, actionable messages (what broke, what to do),
never stack traces. A batch never fails wholesale on one bad image — per-item
errors land in `error_details` while the rest complete.

## The verification pairing

For dataset work where captions become training signal, spot-check what matters:

1. `describe_batch` writes the captions (this tool — generative).
2. Extract the load-bearing claims (species, objects, weapons…).
3. Verify each claim with ai-eyes-mcp's `image_verify` (SigLIP2 —
   discriminative, different model family, measures instead of narrating).

No model verifies its own output; that's the point of the pair.
