#!/usr/bin/env bash
# Run the Ask CK backend test suite + the invariant guards, the same way CI would.
# Uses the repo-local .venv and blocks ~/.local from shadowing the venv's fastapi.
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
echo "ALL GREEN"
