#!/usr/bin/env bash
# verify.sh — imports, tool surface, CI-safe tests, build.
# Mirrors ai-eyes-mcp's verify script. Requires: pip install -e ".[dev]"
set -euo pipefail

echo "== 1/4 imports =="
python -c "
import plain_sight
from plain_sight.engine import Florence2Engine, DETAIL_TASKS
from plain_sight.sidecars import compose_caption, sidecar_path_for, iter_image_files
from plain_sight.cli import build_parser
print('plain-sight', plain_sight.__version__, '— imports OK')
"

echo "== 2/4 MCP tool surface =="
python -c "
import asyncio
from plain_sight.server import mcp
tools = asyncio.run(mcp.list_tools())
names = sorted(t.name for t in tools)
expected = {'describe_image', 'describe_batch', 'read_text', 'sight_status', 'sight_selftest'}
missing = expected - set(names)
assert not missing, f'missing tools: {missing}'
print('tools:', ', '.join(names))
"

echo "== 3/4 CI-safe tests =="
# Project-local basetemp: immune to stale/broken system temp dirs.
python -m pytest tests/test_edge_cases.py -q --basetemp .pytest-tmp

echo "== 4/4 build =="
python -m build >/dev/null
echo "wheel + sdist built OK"

echo "VERIFY PASSED"
