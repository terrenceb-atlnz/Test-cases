#!/usr/bin/env bash
# Start the Ask CK per-user local agent.
# Run this on YOUR OWN machine, then open the shared Ask CK page and pick
# "Claude Code CLI (my local machine)" in LLM -> Configure.
#
#   ./run-agent.sh
#   CK_AGENT_ORIGIN=http://ck-box.lan:8000 ./run-agent.sh   # lock CORS to your server
set -euo pipefail
cd "$(dirname "$0")"
exec python3 ck_agent.py
