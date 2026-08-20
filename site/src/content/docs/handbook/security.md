---
title: Security
description: The threat model — what plain-sight touches, what it never does, and how to report.
sidebar:
  order: 6
---

plain-sight operates **locally only**.

## What it touches

- **Local image files** — opened read-only, never modified.
- **The HuggingFace model cache** — written once on first download.
- **`.txt` caption sidecars** — the ONLY files it writes, only where the caller
  asked (next to the image, or the given `out_dir`), and existing sidecars are
  only replaced under an explicit `overwrite`.

## What it never does

- **No network egress at runtime.** The model downloads once on first use;
  after that all inference is local.
- **No remote code execution.** The engine uses transformers' *native*
  Florence-2 classes only — `trust_remote_code` is never passed, so no
  hub-fetched Python ever executes. This is why the model pin is the
  `florence-community` conversion rather than the `microsoft/` originals.
- **No secrets handling, no telemetry.** Nothing is read from or sent anywhere.
- **No raw stack traces.** MCP clients get structured `ToolError` messages; the
  CLI prints one structured error line. Tracebacks exist only server-side at
  `PLAIN_SIGHT_LOG_LEVEL=DEBUG`.

## Honesty contract

Descriptions are generative and can hallucinate detail. That is a property of
the model class, stated rather than hidden: `sight_status` carries the guidance
in-band, and the recommended pattern for load-bearing claims is verification
with a different model family
([ai-eyes-mcp](https://github.com/mcp-tool-shop-org/ai-eyes-mcp), SigLIP2).

## Reporting

Email **64996768+mcp-tool-shop@users.noreply.github.com** or open an issue at
[mcp-tool-shop-org/plain-sight](https://github.com/mcp-tool-shop-org/plain-sight/issues).
Include a description, steps to reproduce, the version affected, and potential
impact. Targets: acknowledge in 48 hours, assess severity in 7 days, fix within
30 days. Supported versions are listed in
[SECURITY.md](https://github.com/mcp-tool-shop-org/plain-sight/blob/main/SECURITY.md).
