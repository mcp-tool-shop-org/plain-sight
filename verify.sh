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
# Relocate pytest's temp root. --basetemp is not used: pytest deletes that
# directory at every session start, which bricked the suite (Wave 1 PS-006).
# PYTEST_DEBUG_TEMPROOT has no wipe-on-start semantics. mkdir first — pytest
# does not create the parent.
mkdir -p .pytest-temproot
export PYTEST_DEBUG_TEMPROOT="$(pwd)/.pytest-temproot"
python -m pytest -m "not dogfood" -q

echo "== 4/4 build =="
python -m build >/dev/null
echo "wheel + sdist built OK"

echo "VERIFY PASSED"
