#!/usr/bin/env bash
#
# Helper script to start Ask CK (server-backed test tooling workbench)
#
# Usage examples:
#   ./ask-ck/CK-main/run.sh                 # asks: foreground or background?
#   ./ask-ck/CK-main/run.sh --bg            # background, no prompt (fast restart)
#   ./ask-ck/CK-main/run.sh --stop          # stop a backgrounded server
#   ./ask-ck/CK-main/run.sh --restart       # --stop then --bg (fast restart)
#   PORT=9000 ./ask-ck/CK-main/run.sh
#   HOST=0.0.0.0 ./ask-ck/CK-main/run.sh   # EXPOSE ON THE LAN — see the note below
#
# A plain restart needs ONLY this script — it starts against the existing
# ask-ck/var/ck.db in seconds. setup.sh is for first-time setup / DB rebuilds
# (it re-ingests all corpora), which a restart does not require.
#
# Pass extra arguments to uvicorn:
#   ./ask-ck/CK-main/run.sh --log-level debug
#
# This script uses the repo-local .venv automatically if present, sets the
# correct PYTHONPATH for the ask-ck/CK-main/CK_server layout, and (when run
# interactively) asks whether to run in the foreground or the background.
# Data paths are anchored via CK_server/paths.py, so CWD does not matter.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
# CK_RUN_TAG lets a second, throwaway server (E2E / smoke checks — see
# tool/run_scratch_server.sh) keep its own pid + log files, so --stop on one never
# stops or orphans the other. Empty for the normal dev server.
PID_FILE="$REPO_ROOT/.ck-server${CK_RUN_TAG:-}.pid"
LOG_FILE="$REPO_ROOT/.ck-server${CK_RUN_TAG:-}.log"

# --- Stop helper (used by --stop and --restart) -----------------------------
_stop_server() {
  if [ -f "$PID_FILE" ] && CK_PID="$(cat "$PID_FILE")" && [ -n "$CK_PID" ] && kill -- -"$CK_PID" 2>/dev/null; then
    echo "✓ Stopped Ask CK (PID $CK_PID)."
  elif pkill -f 'uvicorn CK_server.main' 2>/dev/null; then
    echo "✓ Stopped Ask CK (matched by process name)."
  else
    echo "• No running Ask CK server found."
  fi
  rm -f "$PID_FILE"
}

# --- Stop mode: `run.sh --stop` ---------------------------------------------
if [ "${1:-}" = "--stop" ] || [ "${1:-}" = "stop" ]; then
  _stop_server
  exit 0
fi

# --- Prompt-free background flags: `--bg` (start) / `--restart` (stop+start) -
# Set RUN_MODE=bg and drop the flag from "$@" so it isn't forwarded to uvicorn.
FORCE_BG=0
case "${1:-}" in
  --bg|-bg)        FORCE_BG=1; shift ;;
  --restart|-restart) FORCE_BG=1; shift; _stop_server; sleep 1 ;;
esac

cd "$SCRIPT_DIR"

# Use the repo-local virtual environment automatically if it exists.
#
# Resolve its interpreter DIRECTLY rather than sourcing `activate` and trusting the PATH
# it sets. `activate` hardcodes the ABSOLUTE path the venv was built at, so after the tree
# moved (copilot/ -> claude/, 2026-08-17) it exported a VIRTUAL_ENV that no longer existed
# and prepended a non-existent bin/ to PATH. Bare `python3` then silently fell through to
# /usr/bin/python3 — a DIFFERENT interpreter (3.10) with a different site-packages, which
# still had fastapi but NOT sentence-transformers. The server would have started and
# degraded to keyword-only search, the exact silent failure README.md:129 warns about.
# `.venv/bin/python` is a relative symlink, so it survives a move; prefer it and say so.
VPY="$REPO_ROOT/.venv/bin/python"
if [ -x "$VPY" ]; then
  export VIRTUAL_ENV="$REPO_ROOT/.venv"
  export PATH="$REPO_ROOT/.venv/bin:$PATH"
else
  echo "⚠ No repo-local .venv at $REPO_ROOT/.venv — falling back to system python3."
  echo "  Run ./setup.sh to build it; without it the server may lack its dependencies."
  VPY="python3"
fi

# Sensible defaults - real use required (no MOCK). The backend is chosen on the LLM
# Configure page (local vLLM / Claude CLI / Grok CLI); LLM_API_KEY and LLM_BASE_URL were
# removed 2026-08-04 — there is no environment-key fallback and no configurable endpoint.
: "${PORT:=8000}"
# Bind to loopback by DEFAULT. Ask-CK has no authentication of any kind, and several
# endpoints have real-world side effects — most sharply
# POST /api/wizard/push_to_zephyr/{key}?dry_run=false, which spends the server's own
# JIRA_KEY to overwrite live Zephyr cases. On 0.0.0.0 any host on the LAN could drive
# that with a one-line curl (CORS does not apply to non-browser clients).
#
# The documented model has always been "localhost / single user"; this makes the DEFAULT
# match that contract. Exposing the server on the network is still supported — it is now
# a deliberate opt-in rather than what you get by accident:
#     HOST=0.0.0.0 ./ask-ck/CK-main/run.sh
: "${HOST:=127.0.0.1}"

echo "🚀 Starting Ask CK (server-backed) - real LLM only"
echo "   LLM:  choose a backend on the Configure page (local vLLM / Claude CLI / Grok CLI)"
echo "   Host: ${HOST}"
echo "   Port: ${PORT}"
echo "   URL:  http://localhost:${PORT}/   (use http://, not https://)"
echo
echo

export PYTHONPATH="$SCRIPT_DIR"

# Stand-alone: the semantic-search embedding model is bundled under ask-ck/var/models/
# and loads from disk. Force HuggingFace offline so the server never reaches out to
# huggingface.co at runtime (not to download, not even for a revision check). Ask CK
# depends on nothing external but its own LLM endpoint. (Refreshing the model is a
# deliberate offline step, not a runtime dependency.)
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"

# Foreground or background? --bg/--restart force background with no prompt;
# otherwise ask when interactive, default foreground.
RUN_MODE="fg"
if [ "$FORCE_BG" = "1" ]; then
  RUN_MODE="bg"
elif [ -t 0 ]; then
  read -r -p "Run in [F]oreground or [b]ackground? [F/b] " _ans
  case "${_ans:-}" in [bB]*) RUN_MODE="bg" ;; esac
fi

if [ "$RUN_MODE" = "bg" ]; then
  : >"$PID_FILE"
  # Append (not truncate) so previous runs' logs are preserved.
  { echo; echo "===== Ask CK started $(date '+%Y-%m-%d %H:%M:%S') ====="; } >>"$LOG_FILE"
  # Run under setsid so the server gets its own session/process group. The inner
  # shell records its own PID, then exec-chains into uvicorn (keeping that PID),
  # so we capture the real server PID and can stop the whole group with --stop.
  setsid bash -c 'echo $$ >"$1"; shift; exec "$@"' _ "$PID_FILE" \
    "$VPY" -m uvicorn CK_server.main:app --host "$HOST" --port "$PORT" --reload "$@" \
    >>"$LOG_FILE" 2>&1 &
  sleep 2
  CK_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$CK_PID" ] && kill -0 "$CK_PID" 2>/dev/null; then
    echo "✅ Ask CK is running in the background (PID $CK_PID)."
    echo "   Open:  http://localhost:${PORT}/   (use http://, not https://)"
    echo "   Logs:  tail -f $LOG_FILE"
    echo "   Stop:  ./ask-ck/CK-main/run.sh --stop"
  else
    echo "✗ Server did not stay up. Check the log:  cat $LOG_FILE"
    exit 1
  fi
else
  echo "▶ Running in the foreground (Ctrl-C to stop)."
  exec "$VPY" -m uvicorn \
    CK_server.main:app \
    --host "${HOST}" \
    --port "${PORT}" \
    --reload \
    "$@"
fi
