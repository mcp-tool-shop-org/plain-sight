# plain-sight: how it works

Mapped at 2026-09-25 from commit 953ac4e.

## What this is

5 parts, mostly Python (9 files), TypeScript (2) and JavaScript (1). Work enters through 4 doors; the busiest is CI, which reaches 2 parts. People run plain-sight and plain-sight-mcp.

## What changed since the last map

This is the first map.

## What comes in

1. **CI.** On a pull request touching 8 paths; on a push touching 8 paths; or by hand. Runs src/plain_sight/engine.py, src/plain_sight/server.py and tests/.
2. **Deploy site to GitHub Pages.** On a push to main touching 2 paths; or by hand. Runs site/astro.config.mjs and site/src/.
3. **plain-sight** (a command people run). Runs src/plain_sight/cli.py.
4. **plain-sight-mcp** (a command people run). Runs src/plain_sight/server.py.

## What happens through CI

1. The workflow runs src/plain_sight/engine.py and src/plain_sight/server.py in src and tests/ in tests.

## Who reads the results

CI writes nothing this map can see.

## The other doors

**Deploy site to GitHub Pages** runs site/astro.config.mjs and site/src/, and deploys the site.

**plain-sight** (a command people run) runs src/plain_sight/cli.py.

**plain-sight-mcp** (a command people run) runs src/plain_sight/server.py.

## What breaks what

- **src** is imported only from tests, by 1 part (tests), and sits on the path of 3 doors.

## What tends to change together

No two source files changed together often enough to name.

Window: 180 days; a pair counts from 3 shared commits, since the window holds fewer than 30 qualifying commits.

## What no test touches

Every code part is imported by at least one test.

## Written but never read

No place this map can see is written, so none goes unread.

## Helpers that look duplicated

No two parts export a helper that looks alike.

## Generated, never hand-edited

Nothing in this repository writes to a tracked place this map can see.

## Hand-authored

People write .github/, the repository root and site/; 2 writes with paths built at run time may land here.

## Where to start

.github/workflows/ci.yml → src/plain_sight/server.py → src/plain_sight/engine.py → src/plain_sight/sidecars.py

Read those in order to follow one pull request end to end.

## What this map cannot see

- 2 writes and 1 read use paths built at run time and are not named here.
- Statistics confidence is low: fewer than 30 qualifying commits in the window, and fewer than 20 source files reach 10 revisions.

Regenerate with `npx --yes @dogfood-lab/atlas map`.
