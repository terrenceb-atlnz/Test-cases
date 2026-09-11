#!/usr/bin/env bash
# Launch Ask CK against a THROWAWAY copy of ck.db, on its own port.
#
# Use this for anything that DRIVES the app as a test would — Playwright E2E, curl smoke
# checks after a refactor, manual poking you do not want recorded. A real person operating
# the app SHOULD dirty ask-ck/var/ck.db (a case load writes a session row; that is the tool
# working). A test doing it is worthless data landing in the permanent, LFS-committed
# source of truth, and on 2026-07-28 exactly that had to be undone by hand.
#
#   tool/run_scratch_server.sh --bg          # background, port 8123
#   CK_E2E_PORT=9123 tool/run_scratch_server.sh --bg
#   tool/run_scratch_server.sh --stop        # stops only the scratch server
#
# Three things keep it clear of the real dev server:
#   * CK_DB_PATH  -> a WAL-consistent copy under $TMPDIR (tool/ckdb_scratch.py)
#   * PORT        -> 8123, so it cannot be mistaken for the dev server on 8000
#   * CK_RUN_TAG  -> its own .ck-server-scratch.{pid,log}, so `run.sh --stop` on one
#                    never stops or orphans the other
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

export PORT="${CK_E2E_PORT:-8123}"
export CK_RUN_TAG="-scratch"

# --stop needs no database.
for arg in "$@"; do
  if [ "$arg" = "--stop" ]; then
    exec "$ROOT/run.sh" "$@"
  fi
done

CK_DB_PATH="$("$PY" "$ROOT/tool/ckdb_scratch.py")"
export CK_DB_PATH
echo "▶ scratch ck.db: $CK_DB_PATH"
echo "  the real ask-ck/var/ck.db will NOT be written by this server"

exec "$ROOT/run.sh" "$@"
