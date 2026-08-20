# Security

## Threat model

plain-sight operates **locally only**.

- **Data touched:** local image files (read-only); HuggingFace model cache
  (downloaded once); `.txt` caption sidecars (the ONLY files it writes, at
  caller-specified locations).
- **No network egress at runtime** — the model downloads once on first use,
  then all inference is local.
- **No remote code execution** — the engine uses transformers' native
  Florence-2 classes only; `trust_remote_code` is never passed, so no
  hub-fetched Python ever executes.
- **No secrets handling** — does not read, store, or transmit credentials or
  API keys.
- **No telemetry** — nothing is collected or sent.
- **Bounded writes** — the only mutation is writing caption sidecars where
  the caller asked (`out_dir` or next to the image); images are opened
  read-only and never modified; existing sidecars are only replaced when
  `overwrite` is explicitly set.
- **Structured errors only** — raw stack traces are never exposed to MCP
  clients or CLI users (set `PLAIN_SIGHT_LOG_LEVEL=DEBUG` server-side for
  tracebacks).

## Reporting

Open an issue at https://github.com/mcp-tool-shop-org/plain-sight/issues or
email 64996768+mcp-tool-shop@users.noreply.github.com.
