---
name: seat-files-terminal-open-on-xrdp-display
description: RECURRING on terrenceb-dl — GNOME Files/Terminal "spin then nothing" (Thunar fine) because an xrdp login pushes DISPLAY=:10 (+PATH, XDG_DATA_DIRS) into the shared systemd --user env and D-Bus-activated apps open on the invisible remote display; fix = re-push GNOME's env + nautilus -q; ~/.xsession repair + sssd krb5 renewal applied 2026-09-14, both awaiting their first real test
metadata:
  type: project
---

On the dev workstation `terrenceb-dl`, clicking **Files (Nautilus)** or **Terminal** in GNOME
makes the dock spinner run, then nothing appears — while **Thunar works**. Seen 2026-09-11 and
2026-09-14; recurs after xrdp use. Root cause confirmed 2026-09-14.

**Root cause — a second graphical session steals D-Bus activation.** Terrence also logs into
this box via **xrdp** (`Service=xrdp-sesman`, `Xorg :10`, an XFCE session started by
`~/.xsession`), and leaves it logged in for days. At xrdp login, two SYSTEM scripts run
`dbus-update-activation-environment --systemd`: `/etc/X11/Xsession.d/20dbus_xdg-runtime`
(pushes `DISPLAY XAUTHORITY`) and `95dbus_update-activation-env` (pushes `--all`). Both sessions
share ONE user bus / `systemd --user`, so the shared activation env ends up `DISPLAY=:10.0`, plus
the xrdp session's `PATH` (no `~/.local/bin`, `~/bin`), `XDG_DATA_DIRS` (no `/usr/share/ubuntu`),
`XRDP_*` and `PULSE_SCRIPT`. Every **D-Bus-activated** app — nautilus, gnome-terminal-server,
gedit, gnome-calendar, seahorse; parent = `systemd --user` — then opens on `:10`, invisible from
the local desktop (`:1`); a dock Terminal also loses `~/bin` (login-shell=false; `.bashrc` only
re-adds `~/.local/bin`). GNOME Shell's launch spinner waits for a window on `:1`, times out,
stops. Thunar is launched directly by the shell, so it's fine. Only a fresh xrdp *login*
re-clobbers (`reconnectwm.sh` is absent).

**The 2026-09-11 diagnosis was wrong.** I blamed network-mount stalls and "fixed" it by killing
nautilus — which cannot work here (the respawn inherits `:10`) and was never verified. The mount
problems are real but SECONDARY and a different symptom class (apps in D-state): NFS
`tbhome.st.atlnz.lc` (= `/media/terrenceb/mnt/testbox_home`) had 867 "not responding" timeouts
on 2026-09-10; the CIFS drives J/K/P/W/I/H (`svr-chch-cifs1`, `sec=krb5`) enter a failed-SessSetup
loop whenever the krb5 ticket expires — 3.8M journal lines in 21 days; fired 07:27 on 2026-09-14.

**Diagnose in 30 s (read-only):**
`systemctl --user show-environment | grep DISPLAY` → `:10` = this issue.
`tr '\0' '\n' < /proc/$(pgrep -x nautilus)/environ | grep DISPLAY`; `loginctl list-sessions`;
`DISPLAY=:10 XAUTHORITY=/run/user/1971/gdm/Xauthority xwininfo -root -tree | grep Nautilus`
shows the hidden windows. Nautilus in state **S**, `wchan=do_poll`, answering `gdbus introspect`
= healthy, NOT wedged. Do not chase PIDs or mounts.

**Recovery (verified by Terrence 2026-09-14):** re-push GNOME's env, then restart the
mis-bound instance — `dbus-update-activation-environment --systemd DISPLAY=:1 XAUTHORITY=…
PATH=… XDG_DATA_DIRS=…` (values from `/proc/$(pgrep -x gnome-shell)/environ`), **then**
`nautilus -q`; kill `gnome-terminal-server` **by PID** if present; `systemctl --user
unset-environment XRDP_SESSION XRDP_SOCKET_PATH XRDP_PULSE_SINK_SOCKET XRDP_PULSE_SOURCE_SOCKET
PULSE_SCRIPT`. Kill alone is NOT enough. Never `pkill -f gnome-terminal-server` — `-f` matches
the running shell's own command line and kills it. gnome-shell is untouched.

**Durable fix 1 — APPLIED 2026-09-14 to `~/.xsession` (Terrence's file, with consent):** a
block before the final `exec dbus-launch … xfce4-session` reads the running gnome-shell's
`DISPLAY`, `XAUTHORITY`, `PATH`, `XDG_DATA_DIRS` from `/proc` and re-pushes them `--systemd`. It
runs at Xsession step 99, i.e. *after* the clobber, so it repairs rather than prevents; no-op if
GNOME isn't running. **Unverified until his next xrdp login** — then `show-environment` must
still say `DISPLAY=:1`. The original file was 10 lines ending in the `exec`; drop the block to
revert. (`/etc/X11/Xsession.d` and `/etc/xrdp/startwm.sh` deliberately untouched —
upgrade-fragile, and bypassing Xsession drops im-config/ssh-agent setup.)

**Durable fix 2 — APPLIED 2026-09-14 to `/etc/sssd/sssd.conf` `[domain/atlnz.lc]` (sudo, with
consent):** `krb5_renew_interval = 30m`, `krb5_renewable_lifetime = 7d`; `sssctl config-check`
clean, sssd restarted, Online. sssd (2.6.3, `auth_provider = krb5`, pam_sss issues the ticket at
login/unlock) had NO renewal before, so the 10 h ticket died every night → the CIFS loop.
**Takes effect from his next login/unlock; unverified** — `klist` renew-until should then be
~7 days out; if it still says 24 h, the KDC capped it and this only bridges overnights.
Root-only backup: `/etc/sssd/sssd.conf.bak-2026-09-14`. Never cat this file into a transcript —
it may hold an LDAP bind secret; use `diff -U0` / key-only greps.

**Why:** Terrence asked to have this surfaced next session; it recurs and the first diagnosis
misled us for a day. **How to apply:** on "Files/Terminal won't open", run the 30-s diagnosis
first; if `DISPLAY=:10`, do the recovery. If either durable fix is still unverified, verify it
(see above) before assuming the problem is solved. The seat's user is the verifier for anything
visual — see [[verify-through-user-not-gui-tests]]. Related: [[askck-lan-hosting]] (the working
tree and the :8000 server live on the same NFS share).
