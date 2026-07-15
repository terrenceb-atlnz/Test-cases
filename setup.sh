#!/usr/bin/env bash
#
# One-shot bootstrap for the Ask CK workbench.
#
# Does the full first-time setup in order:
#   1. cd to the repo root (wherever this script lives)
#   2. check git-lfs >= 3.3 (offer to install/upgrade), then install + pull
#   3. create a Python virtual environment (.venv) if missing
#   4. activate it and install ask-ck/CK-main/requirements.txt
#   5. offer to start the server (run.sh then asks foreground or background)
#
# Safe to re-run: every step is idempotent. Any argument you pass is
# forwarded to run.sh when the server starts, e.g.:
#   ./setup.sh --port 9000
#
set -euo pipefail

# --- 1. Anchor to the repo root (this script's directory) -------------------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"
echo "▶ Repo root: $REPO_ROOT"

VENV_DIR="$REPO_ROOT/.venv"
REQ_FILE="$REPO_ROOT/ask-ck/CK-main/requirements.txt"
RUN_SH="$REPO_ROOT/ask-ck/CK-main/run.sh"

# --- Stop mode: `./setup.sh --stop` — delegate to run.sh --stop --------------
if [ "${1:-}" = "--stop" ] || [ "${1:-}" = "stop" ]; then
  exec "$RUN_SH" --stop
fi

# --- 2. Git LFS -------------------------------------------------------------
# git-lfs < 3.3 is incompatible with modern git (2.38+) and fails 'git lfs pull'
# on a fresh clone with "cannot add to the index - missing --add option?".
LFS_MIN="3.3.0"

lfs_version()  { git lfs version 2>/dev/null | sed -n 's#.*git-lfs/\([0-9.]*\).*#\1#p'; }
lfs_ok() {
  command -v git-lfs >/dev/null 2>&1 || return 1
  local v; v="$(lfs_version)"
  [ -n "$v" ] && [ "$(printf '%s\n%s\n' "$LFS_MIN" "$v" | sort -V | head -1)" = "$LFS_MIN" ]
}

upgrade_lfs() {
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "  Automatic upgrade only supported on Debian/Ubuntu (apt)."
    echo "  Install manually: https://github.com/git-lfs/git-lfs#installing"
    return 1
  fi
  echo "▶ Installing/upgrading git-lfs via packagecloud (requires sudo)..."
  curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
  # Some systems pin an older git-lfs (e.g. Ubuntu ESM) at a HIGHER apt priority
  # than packagecloud, so a bare 'apt-get install git-lfs' keeps the old version.
  # Install the newest available version explicitly to bypass the pin.
  local best
  best="$(apt-cache madison git-lfs 2>/dev/null | awk -F'|' '{gsub(/ /,"",$2); print $2}' | sort -V | tail -1)"
  if [ -n "$best" ]; then
    echo "  Installing git-lfs=$best (explicit, to override any pinned older version)"
    sudo apt-get install -y --allow-downgrades "git-lfs=$best"
  else
    sudo apt-get install -y git-lfs
  fi
}

if ! lfs_ok; then
  if command -v git-lfs >/dev/null 2>&1; then
    echo "⚠ git-lfs $(lfs_version) is older than $LFS_MIN and can fail 'git lfs pull'"
    echo "  on a fresh clone with 'cannot add to the index - missing --add option?'."
  else
    echo "✗ git-lfs is not installed (required, >= $LFS_MIN)."
  fi
  if [ -t 0 ]; then
    read -r -p "Install/upgrade git-lfs now? (needs sudo) [Y/n] " ANS
    ANS="${ANS:-y}"
  else
    ANS="n"
    echo "  (non-interactive shell — skipping automatic upgrade)"
  fi
  case "$ANS" in
    [yY]|[yY][eE][sS])
      if upgrade_lfs && lfs_ok; then
        echo "✓ git-lfs is now $(lfs_version)"
      else
        echo "⚠ git-lfs still not >= $LFS_MIN. Continuing; 'git lfs pull' may fail."
      fi
      ;;
    *)
      echo "  Skipping upgrade. Manual steps:"
      echo "    curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash"
      echo "    sudo apt-get install git-lfs"
      ;;
  esac
fi

# If git-lfs is still entirely absent there's nothing to run; bail early.
if ! command -v git-lfs >/dev/null 2>&1; then
  echo "✗ git-lfs is required and not installed. Aborting."
  exit 1
fi

echo "▶ Git LFS: install + pull"
git lfs install
if ! git lfs pull; then
  echo "⚠ 'git lfs pull' failed (often the old-git-lfs incompatibility above)."
  echo "  Continuing with Python setup; re-run after upgrading git-lfs."
fi

# --- 3. Virtual environment -------------------------------------------------
if [ ! -d "$VENV_DIR" ]; then
  echo "▶ Creating virtual environment: $VENV_DIR"
  python3 -m venv "$VENV_DIR"
else
  echo "▶ Reusing existing virtual environment: $VENV_DIR"
fi

# --- 4. Activate + install deps --------------------------------------------
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo "▶ Installing dependencies from $REQ_FILE"
python3 -m pip install --upgrade pip >/dev/null
python3 -m pip install -r "$REQ_FILE"

echo
echo "✅ Setup complete."
echo "   Virtual env: $VENV_DIR"
echo "   NOTE: this activated the venv only for this script. To run tool/*.py"
echo "         yourself later, activate it in your shell: source .venv/bin/activate"
echo

# --- 5. Offer to launch -----------------------------------------------------
# Default to No; auto-No if run non-interactively (e.g. piped).
if [ -t 0 ]; then
  read -r -p "Start Ask CK now? [Y/n] " REPLY
  REPLY="${REPLY:-y}"
else
  REPLY="n"
  echo "(non-interactive shell — not starting the server)"
fi

case "$REPLY" in
  [yY]|[yY][eE][sS])
    echo "▶ Launching — run.sh will ask foreground or background ..."
    exec "$RUN_SH" "$@"
    ;;
  *)
    echo "Not starting. When ready, run:  ./ask-ck/CK-main/run.sh"
    ;;
esac
