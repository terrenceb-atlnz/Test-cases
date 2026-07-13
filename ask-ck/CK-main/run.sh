#!/usr/bin/env bash
#
# Helper script to start Ask CK (server-backed test tooling workbench)
#
# Usage examples:
#   ./ask-ck/CK-main/run.sh
#   LLM_API_KEY=sk-... ./ask-ck/CK-main/run.sh
#   PORT=9000 ./ask-ck/CK-main/run.sh
#   HOST=127.0.0.1 ./ask-ck/CK-main/run.sh
#
# Pass extra arguments to uvicorn:
#   ./ask-ck/CK-main/run.sh --workers 1 --log-level debug
#
# This script always uses python3 and sets the correct PYTHONPATH
# for the ask-ck/CK-main/CK_server layout. Data paths are anchored
# via CK_server/paths.py, so the working directory does not matter.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

# Sensible defaults - real use required (no MOCK). Provide LLM_API_KEY or use CLI logins (grok login / claude /login)
: "${LLM_API_KEY:=}"
: "${PORT:=8000}"
: "${HOST:=0.0.0.0}"

echo "🚀 Starting Ask CK (server-backed) - real LLM only"
echo "   LLM_API_KEY=${LLM_API_KEY:-'(not set - use grok_cli or claude_code)'}"
echo "   Host: ${HOST}"
echo "   Port: ${PORT}"
echo "   URL:  http://${HOST}:${PORT}"
echo
echo "Note: MOCK/demo mode removed. Configure subscription CLI login or API key for real testing."
echo

PYTHONPATH="$SCRIPT_DIR" exec python3 -m uvicorn \
  CK_server.main:app \
  --host "${HOST}" \
  --port "${PORT}" \
  --reload \
  "$@"
