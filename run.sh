#!/usr/bin/env bash
#
# Root convenience wrapper for the Ask CK server launcher.
#
# run.sh is the primary way to start/stop/restart the server day-to-day (setup.sh
# is only for first-time setup / DB rebuilds). The real launcher lives next to the
# server at ask-ck/CK-main/run.sh (it anchors its paths relative to that location);
# this wrapper just forwards to it so you can run ./run.sh from the repo root.
#
# All arguments and environment are passed straight through, e.g.:
#   ./run.sh                # asks foreground or background
#   ./run.sh --bg           # background, no prompt (fast restart)
#   ./run.sh --restart      # stop + background start
#   ./run.sh --stop         # stop the background server
#   PORT=9000 ./run.sh
#
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$REPO_ROOT/ask-ck/CK-main/run.sh" "$@"
