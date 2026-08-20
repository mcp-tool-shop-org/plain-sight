# Ship Gate

> No repo is "done" until every applicable line is checked.

**Tags:** `[all]` every repo · `[npm]` `[pypi]` `[vsix]` `[desktop]` `[container]` published artifacts · `[mcp]` MCP servers · `[cli]` CLI tools

**Detected:** `[all]` `[pypi]` `[mcp]` `[cli]`

---

## A. Security Baseline

- [x] `[all]` SECURITY.md exists (report email, supported versions, response timeline) (2026-08-20)
- [x] `[all]` README includes threat model paragraph ("Security and Trust": data touched, data NOT touched, the one bounded write) (2026-08-20)
- [x] `[all]` No secrets, tokens, or credentials in source or diagnostics output (2026-08-20)
- [x] `[all]` No telemetry by default — stated explicitly in README + SECURITY.md (2026-08-20)

### Default safety posture

- [x] `[cli|mcp|desktop]` The only mutating action (replacing an existing caption sidecar) requires explicit `--overwrite` / `overwrite=true`; everything else is read-only (2026-08-20)
- [x] `[cli|mcp|desktop]` File operations constrained to known directories — sidecars land next to the source image or in the caller's `out_dir`, nowhere else (2026-08-20)
- [x] `[mcp]` Network egress off by default — one-time HuggingFace model download on first load; zero egress at inference; `trust_remote_code` never used (2026-08-20)
- [x] `[mcp]` Stack traces never exposed — structured `ToolError` results only; tracebacks at DEBUG server-side (2026-08-20)

## B. Error Handling

- [x] `[all]` Errors are actionable structured strings: CLI prints `plain-sight: [CODE] message — hint`; MCP raises `ToolError` with embedded hints (missing path → check path; OOM → `PLAIN_SIGHT_DTYPE=float16` / `PLAIN_SIGHT_DEVICE=cpu`). Deliberate message-string form for LLM callers, mirroring ai-eyes-mcp (2026-08-20)
- [x] `[cli]` Exit codes: 0 ok · 1 user error (incl. usage — argparse's native 2 overridden) · 2 runtime error (internal, failing selftest) · 3 partial success (batch) (2026-08-20)
- [x] `[cli]` No raw stack traces without debug — catch-all formats one structured line; `PLAIN_SIGHT_LOG_LEVEL=DEBUG` for tracebacks (2026-08-20)
- [x] `[mcp]` Tool errors return structured results — validation runs BEFORE model load; server never crashes on bad input (CI-safe test suite proves it) (2026-08-20)
- [x] `[mcp]` SKIP: stateless server — no state/config files to corrupt; the model cache is HuggingFace's own (redownload recovers)
- [x] `[desktop]` SKIP: not a desktop app
- [x] `[vscode]` SKIP: not a VS Code extension

## C. Operator Docs

- [x] `[all]` README is current: what it does, install, usage, platforms (Python >= 3.10, CUDA optional, CPU fallback) (2026-08-20)
- [x] `[all]` CHANGELOG.md (Keep a Changelog format) (2026-08-20)
- [x] `[all]` LICENSE (MIT) present; support status in README Security and Trust + SECURITY.md supported versions (2026-08-20)
- [x] `[cli]` `--help` accurate — argparse-generated for all 5 subcommands and every flag (2026-08-20)
- [x] `[cli|mcp|desktop]` Logging levels: `PLAIN_SIGHT_LOG_LEVEL` (DEBUG/INFO/WARNING/ERROR), stderr only, `plain_sight` logger; no secrets handled at any level (2026-08-20)
- [x] `[mcp]` All 5 tools documented with description + parameters (README table + docstrings with pydantic Field descriptions) (2026-08-20)
- [x] `[complex]` SKIP: no background daemons or operational modes

## D. Shipping Hygiene

- [x] `[all]` `verify.sh` exists: imports + MCP tool surface + CI-safe tests + wheel/sdist build (2026-08-20)
- [x] `[all]` Version in manifest (1.0.0) matches git tag v1.0.0 (tag cut at release step of this treatment) (2026-08-20)
- [x] `[all]` Dependency scanning: `pip-audit` runs in CI (advisory/non-blocking — heavy ML deps carry many non-actionable advisories, same policy as ai-eyes-mcp) (2026-08-20)
- [x] `[all]` SKIP: Dependabot not added per org Actions-cost policy; dep updates handled manually with `pip-audit` advisories in CI
- [x] `[npm]` SKIP: not an npm package
- [x] `[pypi]` `python_requires` set (`requires-python = ">=3.10"`) (2026-08-20)
- [x] `[pypi]` Clean wheel + sdist build (`python -m build` in verify.sh) (2026-08-20)
- [x] `[vsix]` SKIP: not a VS Code extension
- [x] `[desktop]` SKIP: not a desktop app

## E. Identity (soft gate — does not block ship)

- [ ] `[all]` Logo in README header
- [ ] `[all]` Translations (polyglot-mcp, 8 languages)
- [ ] `[org]` Landing page (@mcptoolshop/site-theme)
- [ ] `[all]` GitHub repo metadata: description, homepage, topics

---

## Gate Rules

**Hard gate (A-D):** Must pass before any version is tagged or published.
If a section doesn't apply, mark `SKIP:` with justification — don't leave it unchecked.

**Soft gate (E):** Should be done. Product ships without it, but isn't "whole."
