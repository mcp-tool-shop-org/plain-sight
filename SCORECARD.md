# Scorecard

> Score a repo before remediation. Fill this out first, then use SHIP_GATE.md to fix.

**Repo:** plain-sight
**Date:** 2026-08-20
**Type tags:** [all] [pypi] [mcp] [cli]

## Pre-Remediation Assessment

Assessed at v0.1.0, immediately before the full treatment (2026-08-20). The
repo was born shipcheck-shaped (architecture borrowed from ai-eyes-mcp), so
the baseline is unusually high for a day-old tool.

| Category | Score | Notes |
|----------|-------|-------|
| A. Security | 7/10 | SECURITY.md + no-remote-code stance existed; missing supported-versions table, response timeline, README threat-model section |
| B. Error Handling | 7/10 | Structured errors + validation-before-load existed; CLI exit codes didn't follow the 0/1/2/3 canon (everything lumped into 1) |
| C. Operator Docs | 9/10 | README/CHANGELOG/LICENSE/--help all current; no handbook |
| D. Shipping Hygiene | 5/10 | verify.sh existed; no CI, no dependency scanning, wheel-only build |
| E. Identity (soft) | 1/10 | GitHub description set; no logo, no translations, no landing page, no topics/homepage |
| **Overall** | **29/50** | |

## Key Gaps

1. No CI at all — no automated test run, no dependency scanning on push.
2. CLI exit codes off-canon: user/runtime/partial outcomes indistinguishable to scripts.
3. Identity layer absent: no logo, translations, landing page, or repo topics.
4. SECURITY.md incomplete (no supported versions / response timeline).

## Remediation Priority

| Priority | Item | Estimated effort |
|----------|------|-----------------|
| 1 | CI workflow (paths-gated, pip-audit, tool-surface check) + exit-code canon | 1 session (Phase 0) |
| 2 | Identity: logo → brand repo, translations, landing page + handbook | 1 session (Phases 1–3) |
| 3 | Metadata, repo-knowledge entry, deploy verification | same session (Phases 4–7) |

## Post-Remediation

Verified by `npx @mcptoolshop/shipcheck audit` at the end of the treatment.

| Category | Before | After |
|----------|--------|-------|
| A. Security | 7/10 | 10/10 |
| B. Error Handling | 7/10 | 10/10 |
| C. Operator Docs | 9/10 | 10/10 |
| D. Shipping Hygiene | 5/10 | 9/10 (Dependabot skipped per org Actions-cost policy) |
| E. Identity (soft) | 1/10 | 10/10 |
| **Overall** | **29/50** | **49/50** |
