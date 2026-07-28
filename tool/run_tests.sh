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

# ck.db must be untouched by the gate. tests/conftest.py copies it to a temp file and
# points CK_DB_PATH there, so nothing here should ever write the real one — this is the
# belt-and-braces check that the isolation still holds.
#
# It compares a CONTENT signature, not a file hash. ck.db is WAL-mode, so a committed
# write lands in ck.db-wal and can leave the main file's bytes and mtime untouched for a
# long time: `md5sum ask-ck/var/ck.db` reported "identical" while a mutated test had in
# fact DELETED a real session row (2026-07-28; recovered from a snapshot). Asking SQLite
# reads main+WAL together and sees the write. ~0.4s.
_CKDB_SIG_BEFORE="$(mktemp)"
_CKDB_SIG_AFTER="$(mktemp)"
trap 'rm -f "$_CKDB_SIG_BEFORE" "$_CKDB_SIG_AFTER"' EXIT
PYTHONNOUSERSITE=1 "$PY" tool/ckdb_signature.py > "$_CKDB_SIG_BEFORE"

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
echo "== ck.db untouched =="
PYTHONNOUSERSITE=1 "$PY" tool/ckdb_signature.py > "$_CKDB_SIG_AFTER"
if ! diff -u "$_CKDB_SIG_BEFORE" "$_CKDB_SIG_AFTER"; then
  echo >&2
  echo "ERROR: the test run CHANGED ask-ck/var/ck.db — the permanent source of truth." >&2
  echo "  ck.db is built once and committed via git-LFS; tests must run against the" >&2
  echo "  isolated copy that tests/conftest.py creates (CK_DB_PATH). Check that the" >&2
  echo "  isolation in tests/conftest.py still runs at IMPORT time: db.get_connection()" >&2
  echo "  caches one connection per thread, so the first connection opened wins." >&2
  echo "  Restore the diffed rows before committing anything." >&2
  exit 1
fi
echo "OK — ck.db content signature unchanged (schema + sessions)."

echo
echo "ALL GREEN"
