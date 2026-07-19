#!/usr/bin/env bash
#
# Helper script to start Ask CK (server-backed test tooling workbench)
#
# Usage examples:
#   ./ask-ck/CK-main/run.sh                 # asks: foreground or background?
#   ./ask-ck/CK-main/run.sh --bg            # background, no prompt (fast restart)
#   ./ask-ck/CK-main/run.sh --stop          # stop a backgrounded server
#   ./ask-ck/CK-main/run.sh --restart       # --stop then --bg (fast restart)
#   LLM_API_KEY=sk-... ./ask-ck/CK-main/run.sh
#   PORT=9000 ./ask-ck/CK-main/run.sh
#   HOST=127.0.0.1 ./ask-ck/CK-main/run.sh
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
PID_FILE="$REPO_ROOT/.ck-server.pid"
LOG_FILE="$REPO_ROOT/.ck-server.log"

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
if [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.venv/bin/activate"
fi

# Sensible defaults - real use required (no MOCK). Provide LLM_API_KEY or use CLI logins (grok login / claude /login)
: "${LLM_API_KEY:=}"
: "${PORT:=8000}"
: "${HOST:=0.0.0.0}"

echo "🚀 Starting Ask CK (server-backed) - real LLM only"
echo "   LLM_API_KEY=${LLM_API_KEY:-'(not set - use grok_cli or claude_code)'}"
echo "   Host: ${HOST}"
echo "   Port: ${PORT}"
echo "   URL:  http://localhost:${PORT}/   (use http://, not https://)"
echo
echo "Note: MOCK/demo mode removed. Configure subscription CLI login or API key for real testing."
echo

export PYTHONPATH="$SCRIPT_DIR"

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
    python3 -m uvicorn CK_server.main:app --host "$HOST" --port "$PORT" --reload "$@" \
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
  exec python3 -m uvicorn \
    CK_server.main:app \
    --host "${HOST}" \
    --port "${PORT}" \
    --reload \
    "$@"
fi
