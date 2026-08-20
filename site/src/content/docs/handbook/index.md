---
title: plain-sight Handbook
description: An AI says what it sees — what plain-sight is, when to reach for it, and how it fits the toolshop.
sidebar:
  order: 0
---

**plain-sight** is a local, MIT-licensed image describer. Point it at an image and
an AI (Florence-2) says what it sees — as a one-line caption, a detailed paragraph,
or the text read off the pixels. It ships as an MCP server for Claude and a CLI for
shells and scripts, sharing one engine.

## When to reach for it

| You want… | Use |
|-----------|-----|
| "What is in this image?" in prose | `describe_image` / `plain-sight describe` |
| `.txt` caption sidecars for a LoRA training set | `describe_batch` / `plain-sight batch` |
| The text visible inside an image | `read_text` / `plain-sight ocr` |
| "Does this image contain X?" as a **score** | [ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp) — not this tool |

## The sibling rule

plain-sight is one half of a deliberate pair:

| | ai-eyes-mcp | plain-sight |
|---|---|---|
| Job | **judges** images | **describes** images |
| Model | SigLIP2 (discriminative) | Florence-2 (generative) |
| Output | calibrated scores | prose / OCR / caption files |
| Failure mode | can't narrate | can hallucinate detail |

Descriptions are generative: fluent, usually accurate, and capable of inventing
detail. plain-sight makes output *reproducible* (deterministic decoding), not
*guaranteed true*. When a specific claim matters, verify it with ai-eyes — the two
tools are different model families by design, so one can check the other.

## Architecture in one glance

```
engine.py    Florence-2 wrapper — no MCP dependency, lazy load,
             validation BEFORE the model loads.
sidecars.py  The training-data contract, pure stdlib: basename
             pairing, bare concatenation, directory expansion.
server.py    FastMCP layer: 5 tools, structured errors.
cli.py       argparse CLI: 5 commands, real exit codes.
```

A cloud sibling of the same contract runs on Comfy Cloud as the
`caption-florence2-v1` workflow (one image per job, metadata-rider use). This
tool is the bulk lane: on a modern GPU it captions at roughly one image per
second, entirely locally.
