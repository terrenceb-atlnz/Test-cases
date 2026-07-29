# Testbox Access & Script Execution (from this host)

How to SSH to a lab testbox from this development host, drive a switch's CLI console, and
run an ATTestSet framework test script on hardware. Grounded in what actually works from
this machine (verified 2026-07-28) plus the mechanism the PyTest Creator uses
(`ask-ck/CK-main/CK_server/pt_exec.py`).

> **Provenance markers below:** ✅ = verified from this host this session · 📄 = from a
> prior session's record (`SESSION_STATE.md` 2026-07-28d) · 🔧 = documented from tool code,
> not personally executed here (needs a testbox profile + `.setup`).

---

## TL;DR — reconnect to tb105 now

```bash
SSH_AUTH_SOCK=/run/user/1971/keyring/ssh ssh tb105
#   then, in the interactive shell on tb105:
u5                       # = minicom --wrap -D /dev/u5  → the x950 stack console
#   Ctrl-A then Q to leave minicom without resetting the port.
```

For automation (minicom needs a TTY, so it can't be driven by one-shot SSH commands), drive
the same serial port with **pyserial on tb105** — see §2.

---

## 0. The one gotcha: SSH auth from this host ✅

This host is a Mac-attached VS Code Remote-SSH session; `git`/`ssh` actually run on the
Linux host, but the **default `SSH_AUTH_SOCK` points at the forwarded Mac agent, which is
empty** — so a plain `ssh tb105` fails `Permission denied (publickey)`. The on-disk
`~/.ssh/id_rsa` is passphrase-encrypted (useless non-interactively). The **working key lives
in the Linux gnome-keyring agent**:

```bash
export SSH_AUTH_SOCK="${XDG_RUNTIME_DIR:-/run/user/1971}/keyring/ssh"   # = /run/user/1971/keyring/ssh
ssh-add -l        # → 2048 SHA256:ob3X… terrenceb@terrenceb-dl (RSA)
```

`~/.bashrc` exports this for **interactive** shells, so a normal terminal `ssh tb105` just
works. **Non-interactive / tool shells must set `SSH_AUTH_SOCK` explicitly** (same reason
`git push` needs the prefix). This is the same key that authenticates GitHub.

---

## 1. SSH to a testbox ✅

Testboxes resolve by short name on the lab DNS; the connection is direct (no jump host):

```bash
SSH_AUTH_SOCK=/run/user/1971/keyring/ssh ssh tb105
```

| Fact (tb105) | Value |
|---|---|
| resolves to | `10.36.200.105`, port 22 (OPEN) ✅ |
| login user | `terrenceb` (from `ssh -G tb105`) |
| the device it fronts | an **8-member x950 stack** 📄 |
| mgmt path | tb105 `eth2` `10.37.105.100/25` ↔ stack `eth0` `10.37.105.6/25` (shared mgmt LAN, no data-plane link) 📄 |

Generalises to any box: `SSH_AUTH_SOCK=$sock ssh tb<NNN>`. `ssh -G tb<NNN>` shows the
resolved host/user without connecting.

---

## 2. Drive a switch's CLI console (for CLI grounding / verifying real output)

On tb105 the stack console is a USB serial port: **`/dev/u5 -> /dev/ttyUSB20`** ✅
(`crw-rw---- root grp_everyone` — group-readable, so it's **shared**; don't collide with
another operator).

**Interactive** 📄: `ssh tb105` → `u5` (minicom, 115200). Leave with `Ctrl-A Q`.

**Programmatic (recommended for scripted grounding)** 📄 — run this **on tb105** (the console
is local to tb105), driving `/dev/u5` directly with pyserial:

```python
# on tb105:  python3 drive.py
import serial, time
s = serial.Serial('/dev/u5', 115200, timeout=1)

def cmd(c, settle=0.4):
    s.write((c + '\r').encode()); time.sleep(settle)
    out = b''
    while True:
        chunk = s.read(4096)
        if not chunk: break
        out += chunk
        if b'--More--' in chunk:            # answer the pager with a space, no newline
            s.write(b' '); time.sleep(settle)
    return out.decode(errors='replace')

s.write(b'\r'); time.sleep(0.3); s.read(4096)   # wake the console, clear banner
cmd('terminal length 0')                        # session-scoped: disable the pager
print(cmd('show interface port1.0.1'))          # read-only 'show' commands only
s.close()
```

**Discipline** 📄: read-only `show` commands, session-scoped `terminal length 0`, leave
nothing on the box. This is how the CLI-grounding session captured real `show interface`
output (`current duplex full, current speed 1000, current polarity mdix`).

---

## 3. Run an ATTestSet framework test script on a testbox 🔧

This is the mechanism `pt_exec.py` (`_connect` / `RunManager._run`) uses for a PyTest
Creator hardware run. Documented from code — not personally executed here (it needs a
testbox profile in gitignored `secrets.testboxes.json` + a `.setup` topology file).

**Preconditions on the box:** `/home/st-art/framework` present (READ-ONLY — never write under
it), passwordless `sudo`, `python3`. `check_profile()` probes exactly these.

**Steps (mirroring `RunManager._run`):**

```bash
sock=/run/user/1971/keyring/ssh
BOX=st-art@<testbox>                         # profile default user is st-art, key auth
WORK=/home/st-art/pytest-create/<CASE_KEY>/<RUN_ID>

SSH_AUTH_SOCK=$sock ssh "$BOX" "mkdir -p $WORK"
SSH_AUTH_SOCK=$sock scp <script>.py <lib>.py <topology>.setup "$BOX:$WORK/"
SSH_AUTH_SOCK=$sock ssh "$BOX" "
  cd $WORK && ln -sfn /home/st-art/framework framework &&
  sudo -n PYTHONPATH=/home/st-art python3 ./<script>.py -s <topology>.setup -v
"
```

- The `-s <…>.setup` argument names the topology file (`SETUP-FILE-REFERENCE.md`); the
  script binds device roles from it (`init_swi('swi_a')`, `init_portlink(...)`) and never
  hardcodes a port.
- Results are the framework's stdout; `pt_exec.parse_framework_log()` turns it into
  per-TestCase PASS/FAIL. On a hang (e.g. a physical step waiting on an operator) keep the
  partial output — do not discard completed TestCases.
- **Framework read-only guard:** never redirect/`cp`/`rsync`/interpret into
  `/home/st-art/framework`; copy any file you must edit into the run workdir first
  (`_assert_write_allowed` / `_assert_command_allowed` enforce this in the tool).

> Note: tb105 fronts a switch **console** (§2); a framework run needs a testbox whose
> `.setup` declares real `tb-` portlinks to the DUT(s). tb105's `kochi_uni_tb105.setup`
> declares **zero** `tb-` portlinks (no data-plane cabling), so it is a CLI-console box, not
> a data-plane run target. 📄

---

## 4. Quick reference

| Goal | Command |
|---|---|
| Reconnect to tb105 console | `SSH_AUTH_SOCK=/run/user/1971/keyring/ssh ssh tb105` → `u5` |
| Confirm the agent has the key | `SSH_AUTH_SOCK=…/keyring/ssh ssh-add -l` |
| See how a name resolves | `ssh -G tb<NNN>` |
| Probe reachability, no login | `getent hosts tb<NNN>` · `timeout 4 bash -c 'echo > /dev/tcp/tb<NNN>/22'` |
| Non-interactive test connect | `SSH_AUTH_SOCK=…/keyring/ssh ssh -o BatchMode=yes tb<NNN> hostname` |
