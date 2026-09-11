#!/usr/bin/env bash
#
# db_wal_recover.sh — discard a CORRUPT SQLite WAL from a live, systemd-managed server
# WITHOUT letting a checkpoint fold the corruption into the permanent base file.
#
# ── Why this exists ──────────────────────────────────────────────────────────────────
# ask-ck/var/ck.db runs in WAL mode (db.py: PRAGMA journal_mode=WAL). On 2026-09-03 the
# base file was intact (integrity_check ok read alone) but its uncommitted -wal overlay
# was malformed, and the gate's ckdb_signature.py aborted with "database disk image is
# malformed". The safe fix is to throw the WAL away and keep the good base — but two
# traps make a naive "kill it and rm the wal" corrupt the source of truth:
#
#   1. GRACEFUL STOP -> CHECKPOINT. systemctl stop / ck off / run.sh --stop send SIGTERM.
#      uvicorn shuts down cleanly, SQLite's last-connection-close runs a checkpoint, and
#      the corrupt WAL is folded into the base. (Proven: PRAGMA wal_checkpoint on a copy
#      turned an ok base malformed.) The stop MUST be SIGKILL — no clean close, no
#      checkpoint.
#   2. Restart=always -> RESPAWN. A bare `kill -9` leaves the unit active, so systemd
#      respawns within RestartSec and the new server opens base+corrupt-WAL and may
#      checkpoint on its own. The stop MUST also mark the unit inactive.
#
# This script gets both right: a transient drop-in makes `systemctl --user stop` deliver
# SIGKILL to the whole cgroup (no checkpoint), and the explicit stop marks the unit
# inactive (no respawn) so the WAL can be removed in a window where nothing holds the DB.
#
# ── What is actually true about trap 1 (measured, 2026-09-03) ────────────────────────
# A CORRUPT WAL fails to checkpoint: SQLite's checkpoint-on-close cannot apply it and
# leaves the base untouched. In a controlled rehearsal, base-only integrity stayed `ok`
# even AFTER a naive graceful `systemctl stop` on the corrupt-WAL DB — the corruption is
# what stops the checkpoint, which is why the live base survived 19h. So SIGKILL here is
# CONSERVATIVE defense-in-depth, not the sole thing standing between you and a wrecked
# base: it guarantees no checkpoint is even ATTEMPTED, covering the edge case of a WAL
# whose leading frames are valid and could be partially applied before the corrupt one.
# There is zero downside (we discard the WAL regardless), so we keep it.
# (An earlier claim that a graceful stop "corrupts the base" was a measurement error —
#  base+WAL was read as if it were base-only. It does not.)
#
# ── Fail-closed contract ─────────────────────────────────────────────────────────────
#   * The WAL is NEVER discarded unless the base file, read ALONE, is integrity_check ok.
#     (If the base itself is bad, discarding the WAL could destroy the only good data —
#     we abort and leave everything for a human.)
#   * The base + wal + shm are backed up before anything is stopped or removed.
#   * If post-discard integrity is not ok, the base/wal/shm are RESTORED from that backup,
#     normal service config is re-armed, the server is left STOPPED, and we exit non-zero.
#
# ── Usage ────────────────────────────────────────────────────────────────────────────
#   tool/db_wal_recover.sh                       # real service + real DB (defaults below)
#   CK_RECOVER_SERVICE=ask-ck-scratchrec.service \
#     CK_RECOVER_DB=/tmp/.../rehearse/var/ck.db \
#     tool/db_wal_recover.sh                     # rehearsal against a throwaway unit
#
# The SAME script is used to rehearse on a scratch systemd unit and to run for real; only
# the two env vars change. Rehearse first (see the runbook: tool/DB-WAL-RECOVERY.md).
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SERVICE="${CK_RECOVER_SERVICE:-ask-ck.service}"
DB="${CK_RECOVER_DB:-$ROOT/ask-ck/var/ck.db}"
DROPIN_DIR="$HOME/.config/systemd/user/${SERVICE}.d"
DROPIN="$DROPIN_DIR/zz-wal-recover-killhard.conf"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${CK_RECOVER_BACKUP_DIR:-$ROOT/ask-ck/var/wal-recover-backup-$STAMP}"

say()  { printf '\n\033[1m▶ %s\033[0m\n' "$*"; }
info() { printf '  %s\n' "$*"; }
die()  { printf '\n\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# ── CRITICAL: never let a diagnostic become the WAL's last-closer ─────────────────────
# A plain `sqlite3 <db>` on a WAL-mode database opens read-write, and when it is the LAST
# connection to close, SQLite checkpoints the WAL into the base and deletes -wal/-shm. If
# the WAL is corrupt, that closing checkpoint corrupts the base — the exact failure this
# tool exists to prevent. So EVERY pre-stop integrity probe here runs on a private COPY,
# never on the live files. (A live server holding the DB open incidentally protects it by
# never leaving us as last-closer, but this tool must not depend on that being true.)

integrity_base_only() {
  # Integrity of the base file ALONE (no WAL): copy only the main file, then check it.
  local src="$1" tmp
  tmp="$(mktemp "${TMPDIR:-/tmp}/ck-baseonly-XXXXXX.db")"
  cp "$src" "$tmp"
  local out; out="$(sqlite3 "$tmp" 'PRAGMA integrity_check;' 2>&1 | head -1)"
  rm -f "$tmp"
  printf '%s' "$out"
}

integrity_with_wal() {
  # Integrity of base+WAL together, on a COPY so any checkpoint-on-close hits the copy,
  # never the live source of truth.
  local src="$1" dir
  dir="$(mktemp -d "${TMPDIR:-/tmp}/ck-withwal-XXXXXX")"
  cp "$src" "$dir/probe.db"
  [ -f "$src-wal" ] && cp "$src-wal" "$dir/probe.db-wal"
  [ -f "$src-shm" ] && cp "$src-shm" "$dir/probe.db-shm"
  local out; out="$(sqlite3 "$dir/probe.db" 'PRAGMA integrity_check;' 2>&1 | head -1)"
  rm -rf "$dir"
  printf '%s' "$out"
}

command -v systemctl >/dev/null || die "systemctl not found"
[ -f "$DB" ] || die "DB not found: $DB"

say "Target"
info "service : $SERVICE (user unit)"
info "db      : $DB"
info "backup  : $BACKUP_DIR"

if [ ! -f "$DB-wal" ]; then
  info "no $DB-wal present — nothing to discard. Checking base integrity only."
  base="$(sqlite3 "$DB" 'PRAGMA integrity_check;' 2>&1 | head -1)"
  [ "$base" = "ok" ] && { info "integrity_check: ok — clean, no action needed."; exit 0; }
  die "no WAL, but integrity_check is: $base — human needed."
fi

# ── 0. Preconditions ────────────────────────────────────────────────────────────────
say "0. Preconditions"
base_ok="$(integrity_base_only "$DB")"
info "base-only integrity_check: $base_ok"
[ "$base_ok" = "ok" ] || die "base file is NOT ok read alone ($base_ok) — refusing to discard the WAL. Human needed."
combined="$(integrity_with_wal "$DB")"
info "base+WAL   integrity_check: $combined"
if [ "$combined" = "ok" ]; then
  info "base+WAL is already ok — the WAL is NOT corrupt. This tool is for a corrupt WAL; aborting so you don't discard good data."
  exit 0
fi

# ── 1. Backup ───────────────────────────────────────────────────────────────────────
say "1. Backup base + wal + shm -> $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
cp "$DB"      "$BACKUP_DIR/"
cp "$DB-wal"  "$BACKUP_DIR/"
[ -f "$DB-shm" ] && cp "$DB-shm" "$BACKUP_DIR/"
info "backed up: $(ls -1 "$BACKUP_DIR" | tr '\n' ' ')"

# ── 2. Stop hard: SIGKILL (no checkpoint) + inactive (no respawn) ────────────────────
say "2. Stop $SERVICE with SIGKILL, no respawn"
mkdir -p "$DROPIN_DIR"
cat > "$DROPIN" <<'EOF'
# Transient drop-in written by db_wal_recover.sh. Makes `systemctl stop` deliver SIGKILL
# to the whole control group so no clean SQLite close (and thus no checkpoint) can run.
# Removed again by the same script once the WAL has been discarded.
[Service]
KillMode=control-group
KillSignal=SIGKILL
SendSIGKILL=yes
TimeoutStopSec=5
EOF
systemctl --user daemon-reload
systemctl --user stop "$SERVICE" || true   # unit may already be inactive
# Confirm nothing holds the DB anymore.
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if command -v fuser >/dev/null 2>&1 && fuser "$DB" "$DB-wal" >/dev/null 2>&1; then
    sleep 0.5
  else
    break
  fi
done
if command -v fuser >/dev/null 2>&1 && fuser "$DB" "$DB-wal" >/dev/null 2>&1; then
  die "a process still holds $DB after stop — aborting BEFORE touching the WAL. Drop-in left in place: $DROPIN"
fi
info "service stopped; no process holds the DB."

# ── 3. Discard the corrupt WAL ───────────────────────────────────────────────────────
say "3. Discard corrupt WAL"
rm -f "$DB-wal" "$DB-shm"
info "removed $DB-wal and $DB-shm"

# ── 4. Verify — fail-closed with restore ─────────────────────────────────────────────
say "4. Verify base integrity"
after="$(sqlite3 "$DB" 'PRAGMA integrity_check;' 2>&1 | head -1)"
info "integrity_check: $after"
if [ "$after" != "ok" ]; then
  say "!! integrity NOT ok after discard — RESTORING from backup and leaving server STOPPED"
  cp "$BACKUP_DIR/$(basename "$DB")"     "$DB"
  cp "$BACKUP_DIR/$(basename "$DB")-wal" "$DB-wal"
  [ -f "$BACKUP_DIR/$(basename "$DB")-shm" ] && cp "$BACKUP_DIR/$(basename "$DB")-shm" "$DB-shm"
  rm -f "$DROPIN"; systemctl --user daemon-reload
  die "restored base+wal+shm from $BACKUP_DIR. Server left stopped. Human needed."
fi

# ── 5. Re-arm normal service config ──────────────────────────────────────────────────
say "5. Remove transient drop-in, restore normal stop behaviour"
rm -f "$DROPIN"; rmdir "$DROPIN_DIR" 2>/dev/null || true
systemctl --user daemon-reload
info "drop-in removed; normal SIGTERM stop restored for future."

# ── 6. Start + post-checks ───────────────────────────────────────────────────────────
say "6. Start $SERVICE and re-verify"
systemctl --user start "$SERVICE"
sleep 2
systemctl --user is-active "$SERVICE" >/dev/null && info "service active." || die "service did NOT come active — check: systemctl --user status $SERVICE"
final="$(integrity_base_only "$DB")"
info "post-start base-only integrity_check: $final"
[ "$final" = "ok" ] || die "integrity regressed after start ($final) — investigate immediately."

say "DONE — WAL discarded, base intact."
info "backup kept at: $BACKUP_DIR (remove once you are satisfied)"
