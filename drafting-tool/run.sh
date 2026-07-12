#!/usr/bin/env bash
#
# Helper script to start the Objective Drafting Tool (server-backed version)
#
# Usage examples:
#   ./drafting-tool/run.sh
#   LLM_API_KEY=sk-... ./drafting-tool/run.sh
#   PORT=9000 ./drafting-tool/run.sh
#   HOST=127.0.0.1 ./drafting-tool/run.sh
#
# Pass extra arguments to uvicorn:
#   ./drafting-tool/run.sh --workers 1 --log-level debug
#
# This script always uses python3 and sets the correct PYTHONPATH
# for the drafting-tool/ directory layout.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Sensible defaults - real use required (no MOCK). Provide LLM_API_KEY or use CLI logins (grok login / claude /login)
: "${LLM_API_KEY:=}"
: "${PORT:=8000}"
: "${HOST:=0.0.0.0}"

echo "🚀 Starting Objective Drafting Tool (server-backed) - real LLM only"
echo "   LLM_API_KEY=${LLM_API_KEY:-'(not set - use grok_cli or claude_code)'}"
echo "   Host: ${HOST}"
echo "   Port: ${PORT}"
echo "   URL:  http://${HOST}:${PORT}"
echo
echo "Note: MOCK/demo mode removed. Configure subscription CLI login or API key for real testing."
echo

PYTHONPATH=drafting-tool exec python3 -m uvicorn \
  drafting_server.main:app \
  --host "${HOST}" \
  --port "${PORT}" \
  --reload \
  "$@"
