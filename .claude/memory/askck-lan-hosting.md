---
name: askck-lan-hosting
description: "Ask CK is LAN-hosted at http://10.33.22.17:8000/ as systemd user unit ask-ck.service; the front door is the local `ck` command — NONE of it is in the repo, so this memory is the record"
metadata:
  type: project
  verified: 2026-09-02
---

**Since 2026-08-26 the Ask CK server of record runs LAN-exposed on Terrence's workstation
(`terrenceb-dl`, `http://10.33.22.17:8000/`).** Three host-local artifacts make it so, and the
repo contains **none of them** — this memory and SERVER-README "Hosted deployment" are the
record:

1. **`~/.config/systemd/user/ask-ck.service`** — `HOST=0.0.0.0`, `PORT=8000`,
   `Restart=always` (RestartSec=15), `ExecStartPre` probes `.venv/bin/python` so an unmounted
   NFS share fails fast and retries. Runs `run.sh` itself (non-TTY stdin → its foreground
   `exec` path), so venv/PYTHONPATH/offline-model logic stays in run.sh. Linger is enabled →
   starts at boot, survives logout.
2. **`~/.local/bin/ck`** — the one front door: `ck on|off|restart|reload|status|logs|setup|health`.
   On LOCAL disk deliberately: the repo is on NFS, and the wrapper must work exactly when the
   share is down (`ck on` mounts it). `ck reload` = the admin panel's soft in-process reload.
3. **`/etc/fstab` automount** for `tbhome.st.atlnz.lc:/home/terrenceb` →
   `/media/terrenceb/mnt/testbox_home` (`nofail,x-systemd.automount,_netdev,soft`); backup at
   `/etc/fstab.bak-2026-08-26`. `nofail` means a dead share can never hang or fail boot.

**Why `Restart=always`, not `on-failure`:** `run.sh --stop`'s fallback `pkill -f 'uvicorn
CK_server.main'` delivers a *clean* SIGTERM; `on-failure` would treat that as deliberate and
leave the LAN server dead. Tested 2026-08-26: pkill → NRestarts=1, healthy in 20 s; an explicit
`ck off` / `systemctl --user stop` still stays stopped (explicit stop always wins over
Restart=). **How to apply:** manage the hosted server ONLY with `ck` or `systemctl --user`;
never `run.sh --stop`. The admin panel's Restart button is safe (in-process `--reload` cycle,
MainPID never exits — verified).

**A manual `run.sh` server does not merely bypass systemd — it BLOCKS the unit's self-heal
indefinitely, and the symptom looks like a healthy server.** Measured 2026-09-02: a
`run.sh --bg` started the day before (after a SIGKILL of the real one) held port 8000 on
`127.0.0.1`; `Restart=always` then fired every 15 s into "Address already in use" and died,
leaving the unit stuck `activating`, `MainPID=0`, **`NRestarts=53`**. Nothing looked broken —
`curl 127.0.0.1:8000/health` was fully green (`is_permanent_db: true`, embeddings warm, vector
search on) — because a real, working server WAS running; it was simply on the wrong interface,
so only `http://10.33.22.17:8000/` refused. Terrence's report was "the server came up
different, and i cant put my finger on it", which is exactly what this failure feels like.
**How to apply:** when the LAN URL refuses but localhost works, the diagnosis is one command —
`ss -ltnp | grep :8000`. `0.0.0.0:8000` is correct; **`127.0.0.1:8000` means a manual run.sh
server is squatting and the unit is crash-looping behind it** (confirm with `systemctl --user
show ask-ck.service -p MainPID -p NRestarts`). The fix is to kill that PID *by number* — never
`pkill -f`, which has killed the agent's own shell here — and then do nothing: the port frees,
the unit self-heals in ~2 s and answers over the LAN in ~12 s. Do **not** "fix" it with
`HOST=0.0.0.0 ./run.sh --restart`; that just re-creates the squatter, and `run.sh`'s
`: "${HOST:=127.0.0.1}"` default (run.sh:97, deliberate — no auth on this server) is what makes
a plain `run.sh --restart` produce the loopback-only server in the first place.

**The working tree IS production.** `ask-ck.service` runs uvicorn with `--reload` against
`/media/terrenceb/mnt/testbox_home/claude/Test-cases`, so ANY save to a watched `.py` in this
repo hot-reloads the LAN server within about a second — no restart, no warning, every seat on
10.33.22.0/24 affected. Measured 2026-08-31: a mutation check that stripped a fix from
`routers/pytest_create.py` reloaded live (08:44:48) and the restore reloaded it back
(08:45:03), leaving the shared server 15 s without the fix. **How to apply:** do
counterfactual/mutation edits on a COPY or under `git stash` only if you accept a live blip;
otherwise verify against `tool/run_scratch_server.sh` (its own port + throwaway DB), and after
ANY in-tree edit check `journalctl --user -u ask-ck.service | grep StatReload` to confirm the
newest worker started AFTER your final file state. `git status --porcelain` on the edited file
is the authoritative check that the tree — and therefore the live app — is back where you meant
it. Related: [[ask-ck-admin-restart]], [[ckdb-wal-and-test-isolation]].

Known caveats, all accepted explicitly by Terrence on 2026-08-26:
- **No auth, no firewall** (ufw inactive, INPUT policy ACCEPT): the whole 10.33.22.0/24 can
  push to live Zephyr (JIRA key on disk in `secrets.md`), SSH-drive testboxes
  (`secrets.testboxes.json`), and — since Option A — select "Claude Code CLI (this server)"
  and spend this box's Claude seat. Narrowings live in PLAN-llm-mode-selection.md §5.
- **10.33.22.17 is a DHCP lease** (`dynamic` on enp0s31f6); the 0.0.0.0 bind doesn't care,
  bookmarks do. A DHCP reservation would pin it.
- **Not reboot-tested end-to-end** (each link verified individually: automount unit loaded,
  linger on, unit enabled, ExecStartPre retry works).
- The scratch-server workflow ([[ckdb-wal-and-test-isolation]], port 8123) coexists untouched;
  the full gate ran green WHILE the hosted server was serving.

Related: [[ask-ck-admin-restart]] (restart semantics pre-hosting, now qualified),
[[commit-and-push-on-session-end]].
