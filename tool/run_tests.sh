#!/usr/bin/env bash
# Run the Ask CK test suite + invariant guards, the same way CI would:
#   1. invariant guards (db-only, framework-read-only)
#   2. backend unit tests (pytest, in-process — no network/LLM)
#   3. frontend unit tests (Vitest + jsdom — no browser/server/LLM)
# The Playwright E2E is NOT part of this gate — it is sparingly-run (npm run e2e).
#
#   ./tool/run_tests.sh
#
# Exit 0 = everything green. Non-zero = a guard or test failed.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PY=".venv/bin/python"
PYTEST=".venv/bin/pytest"
if [[ ! -x "$PY" ]]; then
  echo "ERROR: repo-local .venv not found. Run ./setup.sh first." >&2
  exit 2
fi

echo "== invariant guards =="
"$PY" tool/guard_db_only.py
"$PY" tool/guard_framework_readonly.py

echo
echo "== pytest =="
if [[ ! -x "$PYTEST" ]]; then
  echo "pytest not installed in .venv — install dev deps:" >&2
  echo "  .venv/bin/pip install -r ask-ck/CK-main/requirements-dev.txt" >&2
  exit 2
fi
PYTHONNOUSERSITE=1 "$PYTEST" -q

echo
echo "== frontend units (vitest/jsdom) =="
if ! command -v npm >/dev/null 2>&1; then
  echo "SKIPPED: npm not on PATH — install Node to run the frontend unit layer." >&2
elif [[ ! -d node_modules/vitest ]]; then
  # Fail loudly rather than skip: a partial gate that silently omits a whole
  # layer reads as "all green" when it isn't.
  echo "ERROR: frontend deps not installed. Run: npm install" >&2
  exit 2
else
  npm test --silent
fi

echo
echo "ALL GREEN"
