#!/usr/bin/env bash
# Build the Svelte app (ask-ck/frontend/ck-main/svelte/, Trent's) into its dist/ and stamp
# dist/.source-sha256 — PLAN-svelte-cutover.md step 2.
#
# dist/ is COMMITTED: the hosted server only serves files (no build step on the server, no CI,
# the working tree is production). tests/test_svelte_app_built.py recomputes the stamp with the
# same algorithm and fails the gate when dist/ is stale. So: edit under svelte/src (or public/,
# index.html, the configs, package*.json), run this, then `git add ask-ck/frontend/ck-main/svelte/dist`
# and commit. The app's own vite.config.js is deliberately untouched — the stamp lives beside the
# build, not in it.
#
# Hash = sha256 over every source file in sorted path order, each as (relative path + "\n" + bytes
# + "\n") — the islands' convention (current/svelte-src/vite.config.js). LC_ALL=C sort == Python's
# sorted() for these ASCII paths.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"      # ask-ck/tools/ -> repo root
APP="$ROOT/ask-ck/frontend/ck-main/svelte"
cd "$APP"

command -v npm >/dev/null 2>&1 || { echo "ERROR: npm not on PATH — install Node to build the Svelte app." >&2; exit 2; }
[[ -d node_modules/vite ]] || { echo "ERROR: Svelte app deps not installed. Run: (cd $APP && npm install --legacy-peer-deps)" >&2; exit 2; }

npm run build --silent          # vite build -> dist/ (Vite empties dist/ first, so a failed build leaves no stamp)

hash="$(find src public index.html vite.config.js svelte.config.js package.json package-lock.json -type f -print0 \
        | LC_ALL=C sort -z \
        | while IFS= read -r -d '' f; do printf '%s\n' "$f"; cat -- "$f"; printf '\n'; done \
        | sha256sum | cut -d' ' -f1)"
printf '%s\n' "$hash" > dist/.source-sha256     # written only AFTER a successful build
echo "built ask-ck/frontend/ck-main/svelte/dist (source-sha256:${hash:0:12}…)"
echo "now: git add ask-ck/frontend/ck-main/svelte/dist && commit"
