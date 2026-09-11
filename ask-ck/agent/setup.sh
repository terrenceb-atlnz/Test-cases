#!/usr/bin/env bash
# Ask CK seat setup — Ubuntu.
#
# Served by the Ask CK server at <server>/setup/setup.sh and run with ONE line copied from
# the Ask CK home page:
#
#     curl -fsSL http://10.33.22.17:8000/setup/setup.sh | bash
#
# What it does, every time it runs (re-running is how you update or repair):
#   Install ✔  find the Claude Code CLI, install it if absent, fix PATH, `claude update`
#   Login   ✔  `claude auth status`; if not logged in, `claude auth login` (opens the browser)
#   Agent   ✔  download/refresh ck-agent from the server, start it (replace a stale one),
#              optionally register it to start at login, and confirm it is up + logged in
# then it opens Ask CK, which runs the final, authoritative check itself.
#
# Contract + design: ask-ck/plans/PLAN-seat-setup-and-per-seat-llm.md §3.3.
#
# Knobs (environment variables, because `curl | bash` cannot take arguments):
#   CK_SERVER=http://host:port   the Ask CK server (the served copy has it filled in)
#   CK_SETUP_AUTOSTART=yes|no|ask  register the agent at login (default: ask once, remember)
#   CK_SETUP_NO_OPEN=1            do not open the browser at the end
#   CK_SETUP_NO_UPDATE=1          skip `claude update`
set -u

CK_SERVER="${CK_SERVER:-__CK_SERVER__}"
case "$CK_SERVER" in __CK_*) CK_SERVER="http://10.33.22.17:8000";; esac
CK_SERVER="${CK_SERVER%/}"
AGENT_PORT="${CK_AGENT_PORT:-8765}"
AGENT_URL="http://127.0.0.1:${AGENT_PORT}"
AGENT_DIR="${HOME}/.local/share/ck-agent"
CONF="${AGENT_DIR}/ck-agent.conf"
UNIT_DIR="${HOME}/.config/systemd/user"
UNIT="${UNIT_DIR}/ck-agent.service"
INSTALL_DIR="${HOME}/.local/bin"

GREEN=$'\e[32m'; RED=$'\e[31m'; DIM=$'\e[2m'; RESET=$'\e[0m'
ok()   { printf '%s✔%s %s\n' "$GREEN" "$RESET" "$*"; }
bad()  { printf '%s✘%s %s\n' "$RED" "$RESET" "$*"; }
note() { printf '%s  %s%s\n' "$DIM" "$*" "$RESET"; }
die()  { bad "$*"; exit 1; }

# `curl | bash` leaves stdin as the pipe; anything interactive must talk to the terminal.
TTY=/dev/tty
have_tty() { [ -r "$TTY" ] && [ -w "$TTY" ]; }

if [ "$(id -u)" = 0 ]; then
  die "Do not run this as root: the agent must run as YOU, the user whose Claude seat it spends."
fi
for tool in curl python3 sha256sum; do
  command -v "$tool" >/dev/null 2>&1 || die "'$tool' is required and not installed (sudo apt install $tool)."
done

echo "Ask CK seat setup — server ${CK_SERVER}"
echo

# ------------------------------------------------------------------------------------------
# Install
# ------------------------------------------------------------------------------------------
find_claude() {
  if command -v claude >/dev/null 2>&1; then command -v claude; return; fi
  for p in "${INSTALL_DIR}/claude" "${HOME}/.claude/local/claude"; do
    if [ -x "$p" ]; then echo "$p"; return; fi
  done
  return 1
}

ensure_path() {
  # The native installer writes ~/.local/bin/claude and does NOT put it on PATH.
  case ":$PATH:" in *":${INSTALL_DIR}:"*) ;; *) export PATH="${INSTALL_DIR}:$PATH";; esac
  local line='export PATH="$HOME/.local/bin:$PATH"'
  local changed=0
  for rc in "${HOME}/.bashrc" "${HOME}/.profile"; do
    [ -f "$rc" ] || continue
    if ! grep -qsE '(\$HOME|~)/\.local/bin' "$rc"; then
      printf '\n# Claude Code CLI (added by Ask CK seat setup)\n%s\n' "$line" >> "$rc"
      changed=1
    fi
  done
  [ "$changed" = 1 ] && note "PATH fixed in your shell config — new terminals will see 'claude'; existing ones need reopening."
  return 0
}

CLAUDE="$(find_claude || true)"
FRESH_INSTALL=0
if [ -z "$CLAUDE" ]; then
  note "Claude Code CLI not found — installing (official installer, needs HTTPS to claude.ai)…"
  if ! curl -fsSL https://claude.ai/install.sh | bash >/dev/null 2>&1; then
    die "Install: the Claude Code installer failed. Check network access to claude.ai and re-run."
  fi
  FRESH_INSTALL=1
  ensure_path
  CLAUDE="$(find_claude || true)"
  [ -n "$CLAUDE" ] || die "Install: installer ran but 'claude' was not found in ${INSTALL_DIR}."
else
  ensure_path
fi

if [ "$FRESH_INSTALL" = 0 ] && [ "${CK_SETUP_NO_UPDATE:-0}" != 1 ]; then
  note "claude update…"
  if ! "$CLAUDE" update >/dev/null 2>&1; then
    note "claude update reported a problem (continuing with the installed version)."
  fi
fi
CLAUDE_VERSION="$("$CLAUDE" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
ok "Install — Claude Code ${CLAUDE_VERSION:-?} at ${CLAUDE}"

# ------------------------------------------------------------------------------------------
# Login
# ------------------------------------------------------------------------------------------
auth_json() { "$CLAUDE" auth status 2>/dev/null; }
logged_in() { auth_json | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: sys.exit(1)
sys.exit(0 if d.get("loggedIn") else 1)'; }
org_name() { auth_json | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("orgName") or "")
except Exception: print("")' 2>/dev/null; }

if ! logged_in; then
  if have_tty; then
    note "Not logged in — starting 'claude auth login' (it opens your browser)…"
    "$CLAUDE" auth login <"$TTY" >"$TTY" 2>&1 || true
  else
    die "Login: not logged in and no terminal to log in from. Run 'claude auth login', then re-run this."
  fi
  logged_in || die "Login: still not logged in after 'claude auth login'. Run it again and re-run this."
fi
ok "Login — logged in$( o="$(org_name)"; [ -n "$o" ] && printf ' as %s' "$o" )"

# ------------------------------------------------------------------------------------------
# Agent
# ------------------------------------------------------------------------------------------
mkdir -p "$AGENT_DIR"
health() { curl -fsS -m 5 "${AGENT_URL}/health" 2>/dev/null; }
health_field() { python3 -c 'import json,sys
d=json.load(sys.stdin); v=d.get(sys.argv[1]); print("" if v is None else (str(v).lower() if isinstance(v,bool) else v))' "$1"; }

MANIFEST="$(curl -fsS -m 15 "${CK_SERVER}/setup/manifest.json" 2>/dev/null)" || die "Agent: cannot reach ${CK_SERVER}/setup/manifest.json — is the Ask CK server up?"
WANT_VERSION="$(printf '%s' "$MANIFEST" | python3 -c 'import json,sys; print(json.load(sys.stdin)["agent_version"])')"
WANT_SHA="$(printf '%s' "$MANIFEST" | python3 -c 'import json,sys; print(json.load(sys.stdin)["files"]["ck_agent.py"])')"

have_sha=""
DOWNLOADED=0
[ -f "${AGENT_DIR}/ck_agent.py" ] && have_sha="$(sha256sum "${AGENT_DIR}/ck_agent.py" | cut -d' ' -f1)"
if [ "$have_sha" != "$WANT_SHA" ]; then
  DOWNLOADED=1
  curl -fsS -m 30 "${CK_SERVER}/setup/ck_agent.py" -o "${AGENT_DIR}/ck_agent.py.new" || die "Agent: download of ck_agent.py failed."
  got="$(sha256sum "${AGENT_DIR}/ck_agent.py.new" | cut -d' ' -f1)"
  [ "$got" = "$WANT_SHA" ] || die "Agent: downloaded ck_agent.py does not match the server's manifest (got ${got:0:12}…)."
  mv -f "${AGENT_DIR}/ck_agent.py.new" "${AGENT_DIR}/ck_agent.py"
  note "ck-agent ${WANT_VERSION} downloaded."
fi

# Config beside the agent: the agent reads it when the environment does not say otherwise.
{
  echo "origin=${CK_SERVER}"
  echo "port=${AGENT_PORT}"
  if [ -f "$CONF" ] && grep -q '^autostart=' "$CONF"; then grep '^autostart=' "$CONF"; fi
} > "${CONF}.new" && mv -f "${CONF}.new" "$CONF"

# Autostart is the user's choice (plan D6): ask once, remember, honour flags.
AUTOSTART_CHOICE="$(grep -s '^autostart=' "$CONF" | cut -d= -f2)"
case "${CK_SETUP_AUTOSTART:-}" in
  yes|no) AUTOSTART_CHOICE="$CK_SETUP_AUTOSTART";;
  ask|"")
    if [ -z "$AUTOSTART_CHOICE" ]; then
      if have_tty; then
        printf 'Start the Ask CK agent automatically when you log in? [Y/n] ' >"$TTY"
        read -r answer <"$TTY" || answer=""
        case "$answer" in n|N|no|NO) AUTOSTART_CHOICE=no;; *) AUTOSTART_CHOICE=yes;; esac
      else
        AUTOSTART_CHOICE=no
        note "No terminal to ask about autostart — not registering it (re-run with CK_SETUP_AUTOSTART=yes to change)."
      fi
    fi;;
esac
grep -q '^autostart=' "$CONF" && sed -i "s/^autostart=.*/autostart=${AUTOSTART_CHOICE}/" "$CONF" || echo "autostart=${AUTOSTART_CHOICE}" >> "$CONF"

running_json="$(health || true)"
running_version=""
[ -n "$running_json" ] && running_version="$(printf '%s' "$running_json" | health_field agent_version)"

stop_running_agent() {
  curl -fsS -m 5 -X POST -H 'Content-Type: application/json' -d '{}' "${AGENT_URL}/shutdown" >/dev/null 2>&1 || true
  for _ in 1 2 3 4 5 6; do health >/dev/null 2>&1 || return 0; sleep 0.5; done
  # An agent older than 1.1.0 has no /shutdown. Find the listener on our port and, only if
  # it is a ck-agent belonging to this user, stop it the hard way.
  if command -v ss >/dev/null 2>&1; then
    for pid in $(ss -ltnpH "sport = :${AGENT_PORT}" 2>/dev/null | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u); do
      if [ -r "/proc/${pid}/cmdline" ] && tr '\0' ' ' < "/proc/${pid}/cmdline" | grep -q 'ck_agent' \
         && [ "$(stat -c %u "/proc/${pid}")" = "$(id -u)" ]; then
        note "Stopping old agent (pid ${pid}, no /shutdown route)…"
        kill "$pid" 2>/dev/null || true
      fi
    done
    for _ in 1 2 3 4 5 6 7 8 9 10; do health >/dev/null 2>&1 || return 0; sleep 0.5; done
  fi
  return 1
}

write_unit() {
  mkdir -p "$UNIT_DIR"
  cat > "$UNIT" <<UNIT
[Unit]
Description=Ask CK per-user local Claude agent (ck-agent) — spends only this user's own seat

[Service]
Type=simple
Environment=CK_AGENT_ORIGIN=${CK_SERVER}
Environment=CK_AGENT_PORT=${AGENT_PORT}
Environment=PATH=${INSTALL_DIR}:/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/env python3 ${AGENT_DIR}/ck_agent.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
UNIT
}

start_agent() {
  if [ "$AUTOSTART_CHOICE" = yes ] && command -v systemctl >/dev/null 2>&1; then
    write_unit
    systemctl --user daemon-reload
    systemctl --user enable --now ck-agent.service >/dev/null 2>&1 || systemctl --user restart ck-agent.service
    note "Agent registered to start at login (systemd --user ck-agent.service)."
  else
    if command -v systemctl >/dev/null 2>&1 && [ -f "$UNIT" ]; then
      systemctl --user disable --now ck-agent.service >/dev/null 2>&1 || true
      rm -f "$UNIT"; systemctl --user daemon-reload
    fi
    # Detach properly: redirect EVERY fd, then exec, so no intermediate bash lingers as
    # the agent's parent holding the caller's stdout. (`( cd && nohup … & )` left exactly
    # that behind on the first Ubuntu run: a `bash` whose fds 1/2 were the caller's pipe,
    # alive for as long as the agent — so `curl … | bash | anything` never saw EOF.)
    (
      cd "$AGENT_DIR" || exit 1
      exec </dev/null >>"${AGENT_DIR}/agent.log" 2>&1
      export CK_AGENT_ORIGIN="$CK_SERVER" CK_AGENT_PORT="$AGENT_PORT"
      exec setsid nohup python3 ck_agent.py
    ) &
  fi
}

if [ -n "$running_json" ] && [ "$running_version" = "$WANT_VERSION" ] && [ "$DOWNLOADED" = 0 ]; then
  # Up-to-date agent already running. If the user just asked for autostart and it is
  # not registered yet, register it (without disturbing the running one).
  if [ "$AUTOSTART_CHOICE" = yes ] && [ ! -f "$UNIT" ] && command -v systemctl >/dev/null 2>&1; then
    stop_running_agent; start_agent
  fi
elif [ -n "$running_json" ]; then
  # A different version, OR the same version with new bytes (a fix without a bump): the
  # running process is stale either way.
  note "Replacing agent ${running_version:-<unknown>} with ${WANT_VERSION}…"
  stop_running_agent || die "Agent: the old agent on port ${AGENT_PORT} did not stop. Stop it and re-run."
  start_agent
else
  start_agent
fi

# Wait for health — the agent runs `claude update` at startup, which can take a while.
final=""
for _ in $(seq 1 90); do
  final="$(health || true)"
  [ -n "$final" ] && break
  sleep 1
done
[ -n "$final" ] || die "Agent: not answering on ${AGENT_URL} after start. Log: ${AGENT_DIR}/agent.log (or: journalctl --user -u ck-agent)."
a_ver="$(printf '%s' "$final" | health_field agent_version)"
a_cli="$(printf '%s' "$final" | health_field claude_cli)"
a_login="$(printf '%s' "$final" | health_field logged_in)"
a_cliver="$(printf '%s' "$final" | health_field cli_version)"
a_hint="$(printf '%s' "$final" | health_field hint)"
[ "$a_cli" = true ] || die "Agent: up (${a_ver}) but it cannot find the Claude CLI. ${a_hint}"
[ "$a_login" = true ] || die "Agent: up (${a_ver}) but the CLI is not logged in as seen by the agent. ${a_hint}"
ok "Agent — ck-agent ${a_ver} up on ${AGENT_URL}, CLI ${a_cliver}, logged in$( [ "$AUTOSTART_CHOICE" = yes ] && printf ', autostart on' )"

echo
echo "All good. Opening Ask CK — the page will run the final check itself."
if [ "${CK_SETUP_NO_OPEN:-0}" != 1 ] && command -v xdg-open >/dev/null 2>&1; then
  ( xdg-open "${CK_SERVER}/?seat-check=1" >/dev/null 2>&1 & )
else
  echo "Open: ${CK_SERVER}/?seat-check=1"
fi
exit 0
