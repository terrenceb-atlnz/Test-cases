---
name: askck-vpn-access
description: "Reaching the hosted Ask-CK (http://10.33.22.17:8000) from a VPN seat: ping works but the browser/curl to :8000 TIMES OUT because the VPN permits ICMP + SSH/RDP but blocks direct internal TCP:8000 — the server is fine; fix is an SSH tunnel (or run the browser ON the seat)"
metadata:
  type: project
  verified: 2026-09-16
---

**Symptom (recurring — Terrence, 2026-09-16):** from a laptop on the corporate VPN
(e.g. `LavenderTown`), `http://10.33.22.17:8000` shows **"connection has timed out"**, and a
terminal confirms the split: `ping 10.33.22.17` succeeds (≈59 ms, 0 % loss) but
`curl -m5 http://10.33.22.17:8000/health` **times out**. It "worked earlier today" because the
browser was running **on the seat itself** (localhost), not on the laptop over the VPN.

**Cause — the VPN, not Ask-CK.** The VPN / corporate firewall permits ICMP and the
remote-access ports (22 SSH, 3389 RDP) to internal hosts but **blocks arbitrary internal app
ports like TCP:8000**. Ping is ICMP so it passes; the TCP SYN to :8000 is dropped on the path,
so `curl` hangs at connect and times out (a *timeout*, not "connection refused" — refused would
be an RST). Nothing is wrong with the server.

**Prove it's the path, not the server, before touching anything** (all from the host / a seat
shell — this box is `terrenceb-dl` @ 10.33.22.17, passwordless `sudo -n` works here):
- `curl -m5 http://127.0.0.1:8000/health` **and** `curl -m5 http://10.33.22.17:8000/health` → both
  **HTTP 200** in ~0.02 s.
- `ss -ltnp | grep :8000` → bound `0.0.0.0:8000` (correct LAN exposure, not `127.0.0.1`).
- `systemctl --user show ask-ck.service -p ActiveState -p SubState -p NRestarts` → `active` /
  `running` / `NRestarts=0`.
- Firewall open: `ufw status` = inactive, `iptables -L INPUT -n` = policy ACCEPT (empty), no nft
  input-hook drops; `nf_conntrack_count` far below `_max`. Established sockets to :8000 are all
  from `10.33.22.17` itself (the seat's own browser). → **Do NOT restart the service** — it is
  healthy, and a restart just blips it for the LAN clients that CAN reach it.

**Fix — SSH tunnel from the laptop (fastest, no IT, no exposure change):**
```bash
ssh -L 8000:localhost:8000 terrenceb@10.33.22.17
```
Leave it open, then browse **`http://localhost:8000`** on the laptop — the browser hits the
tunnel, which forwards to the seat's local :8000, sidestepping the port block. Rides port 22,
which the VPN allows.

**Alternatives:** (a) run the browser **on the 10.33.22.17 seat** via the remote-desktop/xrdp
session — the localhost path that was working all along; (b) have IT permit TCP:8000 from the VPN
pool to 10.33.22.17 — the "proper" fix, but slower, and it **widens exposure of a no-auth
service** (see [[askck-lan-hosting]]: no auth, no firewall, whole 10.33.22.0/24 can drive it), so
it is a deliberate security decision, not just a firewall tweak.

Related: [[askck-lan-hosting]] (the server-of-record hosting + the DIFFERENT `127.0.0.1`-squatter
failure, which looks similar but is a real server fault — distinguish by `ss -ltnp | grep :8000`),
[[seat-files-terminal-open-on-xrdp-display]] (other terrenceb-dl remote-seat quirks).
