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

# git-lfs < 3.3 is incompatible with modern git (2.38+) and fails 'git lfs pull'
# on a fresh clone with "cannot add to the index - missing --add option?".
LFS_MIN="3.3.0"

# Minimum Python. requirements.txt pins fastapi>=0.139, which requires >=3.10;
# on an older interpreter `pip install -r requirements.txt` fails deep with
# "No matching distribution found for fastapi". Catch it up front instead.
PY_MIN="3.10"

# PREFERRED Python: the version the TESTBOX runs (tb470 is on 3.13.5 as of
# 2026-07-28). The server itself is happy on anything >= PY_MIN, so this is not a
# hard floor — but matching the testbox matters for a specific, non-obvious reason:
#
#   The PyTest Creator lints every GENERATED test script with `py_compile` using
#   THIS interpreter, while the script actually executes under the testbox's
#   `python3`. When the two differ, the lint checks the wrong language version:
#   it accepts imports the target removed, and rejects syntax the target accepts.
#   That is exactly how `from distutils.util import strtobool` shipped in the
#   skeleton — valid on 3.10, compiled clean here, and a hard ImportError on the
#   3.13 testbox before a single test ran.
#
# So: prefer the newest available interpreter, and tell the user when the venv is
# older than one that is installed.
PY_PREFERRED="3.13"

# --- Stop mode: `./setup.sh --stop` — delegate to run.sh --stop --------------
if [ "${1:-}" = "--stop" ] || [ "${1:-}" = "stop" ]; then
  exec "$RUN_SH" --stop
fi

# --- 0. Preflight: base toolchain -------------------------------------------
# Everything below assumes these exist. On a fresh Debian/Ubuntu seat two of
# them commonly do NOT: python3 ships without the venv module (python3-venv, so
# `python3 -m venv` dies with "ensurepip is not available"), and minimal cloud
# images often lack curl (used by the git-lfs installer). git-lfs is required to
# materialize the LFS-tracked permanent database (ask-ck/var/ck.db) + embedding
# model the server reads directly (the DB is shipped, not built). When anything is
# missing we offer to install it via the detected package manager, and only fall
# back to printed instructions when non-interactive or on an unknown distro.

# Populate MISSING with the generic names of any absent prerequisite. Python is
# handled separately (ensure_python) because a present-but-too-old interpreter
# needs a different fix than an absent package.
check_prereqs() {
  MISSING=""
  for c in git git-lfs curl python3; do
    command -v "$c" >/dev/null 2>&1 || MISSING="$MISSING $c"
  done
}

# True if $1 is an interpreter on PATH whose version is >= $PY_MIN.
py_ok() {
  command -v "$1" >/dev/null 2>&1 || return 1
  PY_MIN="$PY_MIN" "$1" -c \
    'import os,sys; mn=tuple(map(int,os.environ["PY_MIN"].split("."))); sys.exit(0 if sys.version_info[:2]>=mn else 1)' \
    2>/dev/null
}

# Select the newest usable interpreter into PY (>= PY_MIN, with the venv module),
# offering an accept/decline install of a newer Python when none is found.
ensure_python() {
  PY=""
  # NEWEST FIRST, and bare `python3` LAST. It used to be first, which defeated the
  # stated intent on any seat whose `python3` is older than an installed
  # `python3.1x` — this seat had 3.13.14 available while `python3` was 3.10.12, so
  # setup.sh would have built the venv on 3.10 and silently reintroduced the
  # testbox/lint version mismatch described at PY_PREFERRED above.
  for cand in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if py_ok "$cand"; then PY="$cand"; break; fi
  done
  if [ -z "$PY" ]; then
    local cur; cur="$(python3 --version 2>&1 || echo 'not found')"
    echo "✗ Need Python >= $PY_MIN (fastapi/pydantic floor); found: $cur"
    local pm="" cmd=""
    if   command -v apt-get >/dev/null 2>&1; then pm=apt;    cmd="sudo apt-get update && sudo apt-get install -y python3.12 python3.12-venv python3-pip"
    elif command -v dnf     >/dev/null 2>&1; then pm=dnf;    cmd="sudo dnf install -y python3.12"
    elif command -v pacman  >/dev/null 2>&1; then pm=pacman; cmd="sudo pacman -S --needed python python-pip"
    fi
    if [ -n "$cmd" ] && [ -t 0 ]; then
      echo "  Suggested: $cmd"
      read -r -p "Install a newer Python now? (needs sudo) [Y/n] " ANS
      ANS="${ANS:-y}"
      case "$ANS" in
        [yY]|[yY][eE][sS]) eval "$cmd" || echo "  ⚠ Install command exited non-zero." ;;
        *) echo "  Skipped." ;;
      esac
      for cand in python3.13 python3.12 python3.11 python3.10 python3; do
        if py_ok "$cand"; then PY="$cand"; break; fi
      done
    fi
  fi
  if [ -z "$PY" ]; then
    echo "✗ No Python >= $PY_MIN available. Install one and re-run ./setup.sh :"
    echo "    Debian/Ubuntu:  sudo apt-get install -y python3.12 python3.12-venv python3-pip"
    echo "    Fedora/RHEL:    sudo dnf install -y python3.12"
    echo "    Arch:           sudo pacman -S --needed python python-pip"
    echo "    macOS (brew):   brew install python@3.12"
    exit 1
  fi
  # The chosen interpreter must also carry the venv module (ensurepip).
  if ! "$PY" -c 'import ensurepip, venv' 2>/dev/null; then
    echo "✗ $PY ($("$PY" --version 2>&1)) lacks the venv module."
    echo "  Debian/Ubuntu:  sudo apt-get install -y ${PY}-venv python3-pip   (e.g. python3.12-venv)"
    echo "  then re-run ./setup.sh"
    exit 1
  fi
  echo "  ✓ Using $("$PY" --version 2>&1) ($(command -v "$PY"))"
}

# Echo the install command for $MISSING using whichever package manager exists,
# or nothing if none is supported. Package names differ per distro.
prereq_install_cmd() {
  local pm="" pkgs="" m
  if   command -v apt-get >/dev/null 2>&1; then pm=apt
  elif command -v dnf     >/dev/null 2>&1; then pm=dnf
  elif command -v pacman  >/dev/null 2>&1; then pm=pacman
  else return 0; fi
  for m in $MISSING; do
    case "$pm:$m" in
      apt:python3-venv)    pkgs="$pkgs python3-venv python3-pip" ;;
      dnf:python3-venv)    pkgs="$pkgs python3 python3-pip" ;;
      pacman:python3-venv) pkgs="$pkgs python python-pip" ;;
      pacman:python3)      pkgs="$pkgs python" ;;
      *)                   pkgs="$pkgs $m" ;;
    esac
  done
  # De-dup (e.g. python3-pip can appear twice) while preserving order.
  pkgs="$(printf '%s\n' $pkgs | awk '!seen[$0]++' | tr '\n' ' ')"
  pkgs="${pkgs% }"
  case "$pm" in
    apt)    echo "sudo apt-get update && sudo apt-get install -y $pkgs" ;;
    dnf)    echo "sudo dnf install -y $pkgs" ;;
    pacman) echo "sudo pacman -S --needed $pkgs" ;;
  esac
}

echo "▶ Preflight: checking base toolchain"
check_prereqs
if [ -n "$MISSING" ]; then
  echo "✗ Missing prerequisites:${MISSING}"
  INSTALL_CMD="$(prereq_install_cmd)"
  if [ -n "$INSTALL_CMD" ] && [ -t 0 ]; then
    echo "  Suggested: $INSTALL_CMD"
    read -r -p "Install missing prerequisites now? (needs sudo) [Y/n] " ANS
    ANS="${ANS:-y}"
    case "$ANS" in
      [yY]|[yY][eE][sS]) eval "$INSTALL_CMD" || echo "  ⚠ Install command exited non-zero." ;;
      *) echo "  Skipped."; ;;
    esac
    check_prereqs
  fi
  if [ -n "$MISSING" ]; then
    echo "✗ Still missing:${MISSING}"
    if [ -n "$INSTALL_CMD" ]; then
      echo "  Install with:  $INSTALL_CMD"
    else
      echo "  No supported package manager (apt/dnf/pacman) detected — install manually:"
      echo "    git git-lfs curl python3 (with venv + pip)"
    fi
    echo "  (A distro git-lfs may be older than $LFS_MIN — setup.sh upgrades it below if needed.)"
    exit 1
  fi
  echo "  ✓ Prerequisites installed."
fi
echo "  ✓ git, git-lfs, curl present"
ensure_python

# --- 2. Git LFS -------------------------------------------------------------
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

LFS_PULL_OK=0
if git lfs pull; then
  LFS_PULL_OK=1
else
  echo "⚠ 'git lfs pull' failed (often the old-git-lfs incompatibility above)."
  # Most common cause is a git-lfs older than $LFS_MIN. If so, offer the same
  # accept/decline upgrade — then retry the pull once.
  if ! lfs_ok; then
    if [ -t 0 ]; then
      read -r -p "Upgrade git-lfs and retry the pull now? (needs sudo) [Y/n] " ANS
      ANS="${ANS:-y}"
    else
      ANS="n"
      echo "  (non-interactive shell — not upgrading; re-run after upgrading git-lfs)"
    fi
    case "$ANS" in
      [yY]|[yY][eE][sS])
        if upgrade_lfs && lfs_ok; then
          echo "✓ git-lfs is now $(lfs_version); retrying pull"
          git lfs install
          git lfs pull && LFS_PULL_OK=1
        fi
        ;;
    esac
  fi
fi

if [ "$LFS_PULL_OK" != "1" ]; then
  echo "⚠ LFS content may be incomplete. The permanent database ask-ck/var/ck.db (and"
  echo "  the bundled embedding model) are shipped via Git LFS — the server needs them"
  echo "  materialized. If the DB check below fails, fix LFS and re-run:"
  echo "    git lfs install && git lfs pull"
fi

# --- 3. Virtual environment -------------------------------------------------
# Create with the vetted interpreter ($PY). Reuse an existing venv only if its
# Python still meets PY_MIN — otherwise a stale venv from an older interpreter
# (e.g. a prior failed run) would keep failing the requirements install.
VENV_PY="$VENV_DIR/bin/python3"
if [ -d "$VENV_DIR" ] && py_ok "$VENV_PY"; then
  echo "▶ Reusing existing virtual environment: $VENV_DIR ($("$VENV_PY" --version 2>&1))"
  # An existing venv that merely meets PY_MIN is REUSED, never upgraded — so a seat
  # that later installs a newer Python keeps building generated-script lints against
  # the old one. Say so, with the exact commands, rather than leave it invisible.
  VENV_VER="$("$VENV_PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo '?')"
  BEST_VER="$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo '?')"
  if [ "$VENV_VER" != "$BEST_VER" ]; then
    echo "  ⚠ This venv is on Python $VENV_VER but $BEST_VER is installed."
    echo "    The PyTest Creator lints GENERATED scripts with the venv's interpreter,"
    echo "    while they RUN on the testbox's python3 (tb470: $PY_PREFERRED). A mismatch means"
    echo "    those lints check the wrong language version — that is how a"
    echo "    distutils import (removed in 3.12) once shipped to a 3.13 testbox."
    echo "    To upgrade (no server running, then verify):"
    echo "      $PY -m venv .venv313 && PYTHONNOUSERSITE=1 .venv313/bin/pip install \\"
    echo "        --index-url https://download.pytorch.org/whl/cpu torch"
    echo "      PYTHONNOUSERSITE=1 .venv313/bin/pip install -r ask-ck/CK-main/requirements-dev.txt"
    echo "      PYTHONNOUSERSITE=1 .venv313/bin/pytest -q tests   # must be green first"
    echo "      mv .venv .venv-old && mv .venv313 .venv"
    echo "      grep -rl '\.venv313' .venv/bin .venv/pyvenv.cfg | xargs sed -i 's|\.venv313|.venv|g'"
    echo "      ./tool/run_tests.sh                                # confirm, then rm -rf .venv-old"
  fi
else
  if [ -d "$VENV_DIR" ]; then
    echo "▶ Recreating virtual environment (missing or older than $PY_MIN): $VENV_DIR"
    rm -rf "$VENV_DIR"
  else
    echo "▶ Creating virtual environment: $VENV_DIR"
  fi
  "$PY" -m venv "$VENV_DIR"
fi

# --- 4. Activate + install deps --------------------------------------------
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo "▶ Upgrading pip"
python3 -m pip install --upgrade pip >/dev/null

# Install the CPU-only PyTorch wheel FIRST so requirements' torch resolves to the
# small CPU build instead of the large default (CUDA) wheel. Best-effort — if it
# fails (offline / unsupported platform), the requirements step still tries.
echo "▶ Installing PyTorch (CPU wheel)"
python3 -m pip install --index-url https://download.pytorch.org/whl/cpu torch \
  || echo "  ⚠ CPU torch install failed; requirements.txt will fall back to the default wheel."

echo "▶ Installing dependencies from $REQ_FILE"
python3 -m pip install -r "$REQ_FILE"

# --- 4b. Vector-search capability check (sqlite-vec needs enable_load_extension) ---
echo "▶ Checking semantic/hybrid search capability"
if python3 - <<'PYEOF'
import sys
try:
    try:
        import pysqlite3 as sq
    except ImportError:
        import sqlite3 as sq
    c = sq.connect(":memory:"); c.enable_load_extension(True)
    import sqlite_vec; sqlite_vec.load(c); c.execute("select vec_version()")
    print("  ✓ sqlite-vec loads — semantic/hybrid search is available.")
    sys.exit(0)
except Exception as e:
    print(f"  ⚠ sqlite-vec cannot load ({e.__class__.__name__}: {e}).")
    print("    Keyword search still works fully. On Linux, `pip install pysqlite3-binary`")
    print("    usually fixes it; otherwise use a Python whose sqlite3 has enable_load_extension.")
    sys.exit(1)
PYEOF
then VEC_OK=1; else VEC_OK=0; fi

# --- 4c. Verify ck.db (SHIPPED via Git LFS — the permanent source of truth) --
# ck.db was built ONCE from the original data and is committed via LFS, together
# with its embeddings and the bundled offline model. `git lfs pull` (step 2)
# already materialized it — there is NO build step. We only sanity-check it here.
echo "▶ Verifying ck.db (shipped via Git LFS; not rebuilt)"
if [ ! -s ask-ck/var/ck.db ]; then
  echo "✗ ask-ck/var/ck.db is missing or empty. Run 'git lfs pull' to materialize it."; exit 1
fi
python3 - <<'PY' || { echo "✗ ck.db present but not readable/populated — check 'git lfs pull'."; exit 1; }
import sys; sys.path.insert(0, "ask-ck/CK-main/CK_server")
import db
chk = db.startup_check()
ok = chk.get("ok") and (chk.get("counts", {}).get("zephyr_cases", 0) > 0)
print(f"  ck.db ready={chk.get('ok')} vectors={chk.get('vector_search')} "
      f"embeddings={chk.get('embeddings')} counts={chk.get('counts')}")
sys.exit(0 if ok else 1)
PY
if [ "$VEC_OK" != "1" ]; then
  echo "  (sqlite-vec unavailable on this Python — semantic search degrades to keyword; the shipped vectors are still present.)"
fi

echo
echo "✅ Setup complete."
echo "   Virtual env: $VENV_DIR"
echo "   Database:    ask-ck/var/ck.db — shipped via Git LFS; permanent single source of"
echo "               truth, built once. NOT rebuildable (source couriers retired)."
echo "   NOTE: this activated the venv only for this script. To run the server or"
echo "         tools yourself later, activate it: source .venv/bin/activate"
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
