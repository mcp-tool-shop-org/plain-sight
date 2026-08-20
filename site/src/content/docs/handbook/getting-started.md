---
title: Getting Started
description: Install plain-sight, run your first description, and register the MCP server.
sidebar:
  order: 1
---

## Requirements

- Python >= 3.10
- `transformers >= 4.51` (native Florence-2 support — installed automatically)
- A CUDA GPU is recommended (~2 GB VRAM at FP16). CPU works, just slower.
- ~1.5 GB disk for the model, downloaded once on first use.

## Install

```bash
git clone https://github.com/mcp-tool-shop-org/plain-sight
cd plain-sight
pip install -e .
```

A virtual environment is recommended:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    POSIX: source .venv/bin/activate
pip install -e .
```

## First description

```bash
plain-sight describe path/to/image.png
```

The first call downloads `florence-community/Florence-2-large` (~1.5 GB) and loads
it (~10–20 s on GPU). Every call after that is ~1 s per image at the default
`high` detail tier. Try the tiers:

```bash
plain-sight describe image.png --detail low     # one sentence
plain-sight describe image.png --detail medium  # a few sentences
plain-sight describe image.png                  # full paragraph (default: high)
plain-sight ocr screenshot.png                  # read the text instead
```

Prove the install end-to-end (describes two bundled reference images and checks
the outputs are sane):

```bash
plain-sight selftest
```

## Register the MCP server

Add to your MCP config (Claude Code, or any MCP client):

```json
{
  "mcpServers": {
    "plain-sight": {
      "command": "plain-sight-mcp",
      "env": {
        "PLAIN_SIGHT_MODEL_DIR": "/path/to/hf-cache/hub"
      }
    }
  }
}
```

`PLAIN_SIGHT_MODEL_DIR` is optional — set it (or `HF_HOME`) when you keep model
weights on a specific drive. The server exposes five tools: `describe_image`,
`describe_batch`, `read_text`, `sight_status`, `sight_selftest`. Call
`sight_status` first if you want to check the engine without triggering the
model load.

## Where to go next

- [Usage](../usage/) — the CLI commands and MCP tools in detail, including the
  dataset-captioning lane.
- [Configuration](../configuration/) — every environment variable, device and
  precision guidance, model pinning.
- [Reference](../reference/) — exact parameters, returns, exit codes, and task
  tokens.
