---
name: askck-lan-hosting
description: "Ask CK is LAN-hosted at http://10.33.22.13:8000/ (was 10.33.22.17 until the 2026-10-23 host rebuild) as systemd user unit ask-ck.service; the front door is the local `ck` command — NONE of it is in the repo, so this memory is the record, including what a host rebuild loses"
metadata:
  type: project
  verified: 2026-10-30
---

**Since 2026-08-26 the Ask CK server of record runs LAN-exposed on Terrence's workstation
(`terrenceb-dl`, `http://10.33.22.13:8000/` — it was `http://10.33.22.17:8000/` until the
2026-10-23 rebuild, see below).** Three host-local artifacts make it so, and the repo contains
**none of them** — this memory and SERVER-README "Hosted deployment" are the record:

**terrenceb-dl was rebuilt (fresh Ubuntu 24.04 install, new NIC `enp4s0`) on 2026-10-23, and
the rebuild silently undid most of this.** Found 2026-10-27 because the gate said ".venv not
found" and the unit had restarted 969 times. What was lost, and what put it back:
- `/usr/bin/python3.13` (the repo `.venv` is built on it; Ubuntu 24.04 ships only 3.12) → the
  deadsnakes PPA + `apt-get install python3.13` (Terrence ran it; the PPA add is refused to
  Claude as external code). Same minor version, so the venv needed no rebuild — the full gate
  proved it.
- `loginctl enable-linger` → re-enabled by Terrence.
- the `/etc/fstab` automount line → restored by Claude with consent, backup
  `/etc/fstab.bak-2026-10-27`; inactive until the next reboot because the share was already
  mounted by hand.
- `git-lfs` and `pwsh` (5 agent-parity tests skip without it) → git-lfs reinstalled; pwsh not.
- **the DHCP lease moved: 10.33.22.17 → 10.33.22.13.** Every pointer to `.17` went stale at
  once: the seat-agent unit's `CK_AGENT_ORIGIN` (env beats `ck-agent.conf`, so the agent locked
  CORS to the dead address), the `ck` wrapper's fallback, the installers' fallback, docs,
  memories, bookmarks. **How to apply:** after ANY rebuild of this host, check those five
  things first, and treat an address in a document as a claim to re-check (`ip -4 addr`).

1. **`~/.config/systemd/user/ask-ck.service`** — `HOST=0.0.0.0`, `PORT=8000`,
   `Restart=always` (RestartSec=15), `ExecStartPre` probes `.venv/bin/python` so an unmounted
   NFS share fails fast and retries. Runs `run.sh` itself (non-TTY stdin → its foreground
   `exec` path), so venv/PYTHONPATH/offline-model logic stays in run.sh. Linger is enabled →
   starts at boot, survives logout.
2. **`~/.local/bin/ck`** — the one front door: `ck on|off|restart|reload|status|logs|setup|health`.
   On LOCAL disk deliberately: the repo is on NFS, and the wrapper must work exactly when the
   share is down (`ck on` mounts it). `ck reload` = the admin panel's soft in-process reload.
3. **`/etc/fstab` automount** for `tbhome.st.atlnz.lc:/home/terrenceb` →
   `/media/terrenceb/mnt/testbox_home` (`nofail,x-systemd.automount,_netdev,soft`); backups at
   `/etc/fstab.bak-2026-08-26` and `/etc/fstab.bak-2026-10-27` (re-added after the rebuild).
   `nofail` means a dead share can never hang or fail boot.

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
otherwise verify against `ask-ck/tools/run_scratch_server.sh` (its own port + throwaway DB), and after
ANY in-tree edit check `journalctl --user -u ask-ck.service | grep StatReload` to confirm the
newest worker started AFTER your final file state. `git status --porcelain` on the edited file
is the authoritative check that the tree — and therefore the live app — is back where you meant
it. Related: [[ask-ck-admin-restart]], [[ckdb-wal-and-test-isolation]].

Known caveats, all accepted explicitly by Terrence on 2026-08-26:
- **No auth, no firewall** (ufw inactive, INPUT policy ACCEPT): the whole 10.33.22.0/24 can
  push to live Zephyr (JIRA key on disk in `secrets.md`), SSH-drive testboxes
  (`secrets.testboxes.json` — NO LONGER since 2026-10-12: the server's SSH run path and its
  profiles were removed; runs go through each user's own seat agent), and — since Option A — select "Claude Code CLI (this server)"
  and spend this box's Claude seat. Narrowings live in PLAN-llm-mode-selection.md §5.
- **10.33.22.13 is a DHCP lease** (`dynamic` on `enp4s0`; it was 10.33.22.17 on `enp0s31f6`
  before the 2026-10-23 rebuild — the lease has now moved once for real); the 0.0.0.0 bind
  doesn't care, bookmarks and the seat agents' `CK_AGENT_ORIGIN` do. A DHCP reservation from IT
  would pin it.
- **Not reboot-tested end-to-end** (each link verified individually: automount unit loaded,
  linger on, unit enabled, ExecStartPre retry works). Still true after the 2026-10-27 repair.
- The scratch-server workflow ([[ckdb-wal-and-test-isolation]], port 8123) coexists untouched;
  the full gate ran green WHILE the hosted server was serving.

Related: [[ask-ck-admin-restart]] (restart semantics pre-hosting, now qualified),
[[commit-and-push-on-session-end]].
