# Changelog

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
