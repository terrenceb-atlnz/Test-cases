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

### Which console is which unit — verify, do NOT trust the `.setup` ✅

The `.setup` file is **declarative, not verified**. Its `[switch] = /dev/uN` lines rot as lab
hardware is recabled, and a stale line will point you at a different device entirely. Measured
on tb105, 2026-07-29: `tb105.setup` declared the 8-member `c2_core_stk` x950 stack on
`u16, u10, u24, u5, u17, u23, u6, u18`, but live only **3 of 8** were right — `u16/u17/u18`
fronted **C1-x930-STK**, `u23` fronted **D1-x540-STK-2**, and `u24` did not exist at all.

Parse `.setup` for membership / stackports / cabling (see `SETUP-FILE-REFERENCE.md`), but
resolve consoles against the hardware before driving anything.

**The reliable per-unit identifier is the login BANNER, not the prompt.** On an AlliedWare Plus
VCStack, every member's console serves the full stack-wide CLI and shows the *shared* stack
hostname once logged in (`x950-MAX#` on master and backups alike) — so the prompt cannot tell
you which unit you are on. The banner shows the unit's own name:

| What you see | Means |
|---|---|
| `x950-MAX-5 login:` | member **5** (the `-N` suffix is the stack ID) |
| `x950-MAX login:` (bare, no suffix) | the **Active Master** |
| `x950-MAX#` prompt, no banner | already logged in — identity unknown, send `quit` to force the banner |

That `quit`-to-read-the-banner trick is exactly what `0009_simple_repeated_Master_reboot.py::
get_master_id()` does. Note it **logs out whoever is on that console**.

Sweep **all** of `/dev/u*`, not just the subset `.setup` names — open each at 115200, send `\r`,
read, and match `([\w.-]+) login:`. Skip ports held by another operator (`/var/lock/LCK..*`,
`pgrep minicom`). **42** `/dev/uNN` ports on tb105 as at 2026-07-30 (`u24` does not exist; filter the
glob so `/dev/urandom` is not swept), budget ~2 s each — the whole sweep is ~90 s. Send only `\r` on
the first pass: that identifies anything sitting at a login prompt without disturbing it, and leaves
`quit` (which logs the occupant out) for just the consoles you actually need.

**tb105 `c2_core_stk` (`x950-MAX`, 8 members) as at 2026-07-30 ✅ — re-verify before use:**

| Console | Member | Note |
|---|---|---|
| `u7` | 1 | Active Master at time of survey (bare banner) |
| `u5` | 2 | by elimination — a leftover session held it at `#`, so no banner |
| `u6` | 3 | |
| **`u8`** | **4** | |
| `u10` | 5 | |
| `u11` | 6 | |
| `u12` | 7 | |
| `u9` | 8 | |

> **Corrected 2026-07-30.** This table previously said member 4 had **no console** ("7 consoles for
> 8 members"). Wrong — member 4 is on **`/dev/u8`**, and all 8 members are reachable. The likely
> cause of the miss: the 2026-07-29 sweep ran around a member-reboot loop, and a **booting** unit's
> console emits boot spam rather than a `login:` banner, so `u8` fell into the no-banner bucket.
> **Sweep a quiescent stack**, or a rebooting member reads as an absent one.

Master ID is **not** stable: any failover or rolling reboot re-elects it, so re-read the banners
immediately before a run that targets "the master". The `.setup` slot labels (`c2_core_stk_4`)
are **not** stack IDs.

### Predicting which member becomes master ✅

From `ck.db`'s own CLI reference (`stack priority`, `stack_cmd/stack_priority_ag.html`): **the
lowest priority value wins; where two members share the lowest value, the lowest MAC address
wins.** Default is 128, and *"assigning a new priority value will not immediately change the
current stack master"* — election happens only on reboot, and there is no pre-emption when a
higher-priority unit rejoins.

On tb105, ID 1 is priority **10** and every other member is **128**, so:

| Reboot the master… | …and the new master is |
|---|---|
| ID 1 (priority 10) | **ID 8** — lowest MAC (`e01a.ea43.e462`) among the 128s |
| ID 8 | **ID 1** — priority 10 beats every 128 |

Confirmed on hardware twice on 2026-07-30, so a repeated master-reboot loop alternates **1 ↔ 8**.
Worth knowing before a run: it tells you which console will hold the master next.

### Backup consoles are RELAYED to the master ✅

Logging in on a *backup* member's console does not give you that unit — the Stack Login Server
relays the session to the master. Consequence when the master reboots: **every backup console
session is dropped**, with

```
Read from remote host node-1: Software caused connection abort
```

and the console falls back to its own `login:` banner. So the `has become the Active Master`
promotion message appears **only on the console of the unit that actually won the election** —
watching one arbitrary member and waiting for it is a coin flip. Work out who will win first
(priority, then lowest MAC, above), or sweep every member's banner.

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
Creator hardware run.

> ✅ **The server-side run path is now VERIFIED end to end (2026-08-03).**
> `POST /api/pytest-create/profiles/tb470/check` returns
> `{"ok":true,"ssh":true,"framework":true,"sudo":true,"detail":"tb470\nPython 3.13.5"}`.
> It had never passed before, for a reason that had nothing to do with the lab: **`paramiko`
> was declared in no requirements file**, and because `import paramiko` sits inside
> `_connect()`, the probe answered `"SSH connection failed: No module named 'paramiko'"` —
> which reads as a testbox or network fault. See §3a for the two settings it needs.

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

### 3a. The two things a server-side run needs that are easy to miss ✅

Both verified 2026-08-03 on tb470.

**1. The profile user is `terrenceb`, NOT the `st-art` default.** `st-art@tb470` does *not*
authenticate with the keyring key — `Permission denied (publickey,password)`. `terrenceb@tb470`
does, and it has passwordless `sudo` and `python3` 3.13.5, and can read
`/home/st-art/framework`. So the profile must set `user` explicitly:

```bash
curl -s -X POST localhost:8000/api/pytest-create/profiles -H 'Content-Type: application/json' -d '{
  "name":"tb470","tb_number":"470","host":"tb470","user":"terrenceb","auth":"key",
  "setups":{"tb470":"/home/st-art/st-art/configs/tb470.setup"}}'
curl -s -X POST localhost:8000/api/pytest-create/profiles/tb470/check
```

**2. The SERVER process needs the keyring agent, not just your shell.** `pt_exec._connect`
falls back to `key_path` (`~/.ssh/id_rsa`, passphrase-encrypted and useless
non-interactively) and otherwise relies on paramiko's agent support — i.e. on the *uvicorn
process's* `SSH_AUTH_SOCK`. Started from VS Code it inherits the forwarded **Mac** agent, which
is empty. Export the keyring socket before restarting; `run.sh` passes the environment through:

```bash
export SSH_AUTH_SOCK="${XDG_RUNTIME_DIR:-/run/user/1971}/keyring/ssh"
ssh-add -l                            # must list the RSA key
./ask-ck/CK-main/run.sh --restart
```

⚠️ `run.sh` **always** passes `--reload`, so editing anything under `ask-ck/CK-main` bounces the
server and kills in-flight LLM calls. Sequence server-code edits into idle windows during a long
batch — this cost a mid-run case here.

> Note: tb105 fronts a switch **console** (§2); a framework run needs a testbox whose
> `.setup` declares real `tb-` portlinks to the DUT(s). tb105's `kochi_uni_tb105.setup`
> declares **zero** `tb-` portlinks (no data-plane cabling), so it is a CLI-console box, not
> a data-plane run target. 📄
>
> **Refined 2026-07-29** ✅: that holds for *data-plane* runs only. **Console-only scripts run
> fine on tb105** — a script that just drives the master console (stack reboot/failover loops,
> CLI grounding) needs no portlinks at all, and several were executed there successfully. The
> distinction is portlinks, not "can't run scripts here". Also note tb105 runs as user
> `terrenceb`, not `st-art`, and needs no `sudo` for serial access.

---

## 4. Running a LEGACY corpus script on hardware ✅

Corpus scripts recovered from `ck.db` are mostly 2015-era and **will not run as-is** against the
current framework. Verified 2026-07-29 staging three stack-reboot scripts onto tb105.

### Never patch the source of truth

**`ck.db` and `/home/st-art/framework` are both off-limits for edits** — Terrence: "explicitly
bad things". The workflow is:

1. Extract `scripts.source_text` from `ck.db` (read-only; `sqlite3 'file:…ck.db?mode=ro'`).
2. Verify what you extracted against the stored `scripts.sha1` — the DB holds the whole literal
   file body, so this should match exactly.
3. Write it to a **staging copy**, keep a `.orig` beside it, and patch only the copy.
4. Staging at the **root of testbox_home works with no SCP step** — that path *is*
   `/home/terrenceb` on the testbox over NFS (`10.36.250.11:/home`). Note this is a *shared* lab
   home, not private scratch.

### The four breakages, in the order they bite

| # | Symptom | Fix |
|---|---|---|
| 1 | `SyntaxError: invalid syntax` importing the framework under `python` | **The framework is Python 3 ONLY** (`ATSwitch.py` uses f-strings). Testboxes still ship `python` 2.7 — use `python3` with `PYTHONPATH=/home/st-art`. This then *forces* fixes 2-4. |
| 2 | `AttributeError: 'dict' has no attribute 'iteritems'` | py2-only, and usually inside an arg-logging helper called *before* the main loop, so it dies instantly. → `.items()`. |
| 3 | `AttributeError: can't set attribute` on `dut.name = …` | **`Switch.name` is now a read-only `@property`** (returns `mappedName or setupName`). Assign the underlying attrs: `obj.mappedName = None; obj.setupName = …`. `Switch.name_is()` is a *comparison*, not a setter. |
| 4 | Console won't open, or `TypeError: %d format` | **TBv4 wants a full device path.** A testbox with `/etc/network/interfaces` is TBv4, where `Switch(tty=…)` needs `/dev/u5`, not an int — so `add_argument("device", type=int)` cannot express it. Knock-on: any `'%d' % tty` filename then `TypeError`s, and a raw path in a filename needs its basename. |

Only `name` and `bootsFromFlash` are read-only properties on `Switch`; `logFileName`,
`console.logFileName`, `preCmdBuf` and `preModeBuf` are all still plain attributes. Check the
whole set of attributes a script assigns *before* launching, rather than crash-and-retry.

### Also check: mis-calibrated timeouts, and unexpected config writes

- **Timeouts were tuned for flash-booting units.** tb105's x950 stack **netboots via TFTP**
  (`tftp://10.37.105.100/x950-tb105.rel`, with a bootloader *"forced to boot from a non-standard
  location"* warning). Measured: **5 m 44 s for ONE unit** to reach `Configuration update
  completed`; **6 m 49 s for 7 members rebooted concurrently**. A shipped 300 s stack-reform
  budget is therefore shorter than a single unit's boot and fails spuriously — raise it and say so
  in the log.
- **Several of these scripts write startup-config.** They check for
  `line con 0 / exec-timeout 0 0 / length 0` in `show run` and, if absent, enter config mode and
  `wr`. Read `show running-config | include line|exec-timeout|length` first; if it is already
  present the branch never fires and the DUT config is untouched.

### Worked example — console-only run on tb105

```bash
sock=/run/user/1971/keyring/ssh
# cwd holds the framework's per-device console logs; logDir gets the script's own run log
SSH_AUTH_SOCK=$sock ssh tb105 '
  cd ~/x950-reboot-run &&
  setsid nohup env PYTHONPATH=/home/st-art python3 ~/<script>.py -v \
      <args> /home/terrenceb/ > run.stdout 2>&1 < /dev/null &'
```

- `setsid nohup … < /dev/null &` so the run survives the SSH session closing. These loops run for
  hours; poll the log rather than holding a connection open.
- **Python buffers stdout when redirected**, so `run.stdout` stays *empty* until the process
  exits. Read the script's own log file for live progress, and the framework's
  `<hostname>.log` for the raw console transcript.
- Framework logs are written with `\r` line endings and embedded NULs — `tr -d '\000'` before
  `grep`, or grep reports "binary file matches".
- **Never `pkill -f <script-name>` over SSH**: the pattern matches the remote `bash -c` command
  line carrying it and kills your own session (exit 255). Use `pgrep -f "[s]cript"` to test, and
  kill by the PID you captured.

## 4a. Lessons from de-stacking two IE520s on tb470 (2026-07-30) ✅

Five things that cost real time and are not obvious from any doc.

**A console held by minicom is off-limits — check before you drive it.** Both tb470 consoles
were held by the operator's own `minicom` sessions. Two processes on one serial port interleave
in *both* directions: your reads swallow bytes theirs is waiting on, and your writes land in
their session. Check `ls /var/lock/LCK..*`, `pgrep -a minicom`, and `ps -o user,tty -p <pid>`
before opening anything; the lock file contains the holder PID.

**The console may be the ONLY CLI path.** The IE520s answer on 80/443 but have **no SSH and no
telnet**, and enabling `ssh server` would itself need CLI access. Don't plan around the
management network without probing it first.

**A "bugged out" stack is usually a split one, and the giveaway is `err-disabled`.** Both units
were provisioned into the same virtual chassis with their stackports uncabled, so each saw the
other as merely `Provisioned`. One ran as a standalone Active Master; the other became a
**`Disabled Master`** in "failover mode" with **all 26 front-panel ports `err-disabled`** —
which is why newly-cabled links stayed down. No interface config on the healthy unit could have
fixed a dead far end. Read `show stack detail` on *both* units before touching anything.

**Never use `no stack <id> enable` to unpick this.** Per the CLI reference it "will act as a
stand-alone master and **disable all of its ports**… can then only be accessed via its console
port" — i.e. it *creates* the state you are trying to escape. What worked: `no stackport` on
both 27/28 ranges, `no stack virtual-mac`, **`stack 2 renumber 1`** on the demoted unit
(`show stack` then shows a `Pending ID`), `write`, reboot. Afterwards both read
`Operational Status: Standalone unit` with their own MAC as the stack MAC.

**Two things could not be removed, and one is a live hazard.** On the IE520,
`port1.0.27/1.0.28` are **dedicated** stackports: `no stackport` is accepted and saved, but the
flag returns after reboot on the real member's ports (it sticks only on an absent member's
phantom ports). And `stack virtual-chassis-id` has **no `no` form at all** — `no stack ?` offers
only `<1-8>`, `all`, `disabled-master-monitoring`, `management`, `resiliencylink`,
`virtual-mac`. So both units end up stack ID 1 sharing one chassis-id with live stackports:
**do not cable 27/28 between them** or they will both claim ID 1 and land straight back in
duplicate-master/err-disabled.

### The CLI is media-blind — do not trust it to reject a nonsensical setting ✅

On a **1000BASE-SX fibre** port, `speed ?` still offers `10 … 400000` and `duplex ?` still
offers `half`, identically to a copper port. `polarity {auto|mdi|mdix}` is likewise offered on
fibre, where MDI/MDI-X has no meaning (the docs say it applies to "a copper-based switch port").
Nothing errors. So a speed matrix pointed at fibre records *"DUT failed to set speed 100"* — a
false failure blamed on the product — and a polarity step is a silent no-op.

Media is only knowable from the **pluggable**, via the `Type` column of
`show interface <port> status` (`1000BASE-T`, `10GBASE-TM`, `1000BASE-SX`, or `not present` for
an empty cage — note that value has a space in it). It cannot be inferred from a port name: on
tb470 `port1.0.1` is a 1000BASE-T on one unit and a 10GBASE-TM on the other. `tool/pt_media.py`
classifies it; `ask-ck/pytest-create/TOPOLOGY-PROFILES.md` explains why it must be asserted at
run time rather than declared in a file.

Also worth knowing: mismatched copper modules still link. An AT-SPTXc (1000BASE-T) against an
AT-SP10TM (10GBASE-TM) negotiated 1000/full without complaint.

### Absence from ck.db's CLI reference means UNKNOWN, not unsupported ✅

`polarity` is documented for 29 products **not including `ie520`** — and both tb470 IE520s
support it (confirmed with `polarity ?` in interface config). `ie560` is the only IE5xx in the
harvest at all. Treat a missing product as uncovered by the docs and verify on the device;
`stackport` behaved the same way.

## 4b. tb470 host networking — DHCP, routing, and packet capture (2026-08-04) ✅

Came out of repairing `isc-dhcp-server` on tb470 and then tracing why a switch could not reach
the IDevID provisioning proxy. All of it is host-side; none of it touches the framework.

### 🔑 Only `10.38.215.0/24` has an upstream return path, and tb470 has NO NAT

This is the big one. `nft list ruleset` is **0 bytes** and **`iptables` is not installed**, so
`ip_forward=1` forwards lab traffic with its source address **intact** and relies entirely on
the org network knowing how to route the reply back. It knows `10.38.215.0/24`. It knows
nothing else you invent. Proof, run from tb470 itself:

```bash
dig +time=4 +tries=1 -b 10.38.215.1  @1.1.1.1 pool.ntp.org   # NOERROR, 4 answers, ~150 ms
dig +time=4 +tries=1 -b 10.37.101.1  @1.1.1.1 pool.ntp.org   # timed out
dig +time=4 +tries=1 -b 10.36.201.215 @1.1.1.1 pool.ntp.org  # NOERROR (mgmt address)
```

**⇒ Never move a lab segment off `10.38.215.0/24` without adding NAT first.** Renumbering eth3
to `10.37.101.1/27` cost every client on it all off-segment reachability, and it presents as
"DNS doesn't work" / "the service is unreachable", not as a routing error. `dig -b <addr>` is
the cheapest way to separate *destination unreachable* from *source unroutable* — the same
query differs only by source address.

`named` needs no attention across a renumber: it has no explicit `listen-on`, binds all
interfaces and re-binds within ~60 s by itself. It is **not** a usable resolver, though —
`named.conf.options` holds only `directory`, no zones and no forwarders, and it times out on
every address it listens on.

### A failing `isc-dhcp-server` hides its reason from unprivileged `journalctl`

The unit is an **LSB init wrapper** (`/etc/init.d/isc-dhcp-server`, systemd-sysv-generated), so
it only reports `Starting ISC DHCPv4 server: dhcpdcheck syslog for diagnostics. ... failed!`.
The real reason is logged by `dhcpd` itself at a privileged level:

```bash
sudo journalctl -u isc-dhcp-server --no-pager -n 40    # sudo is NOT optional here
```

**`dhcpd -t` is not a startup check.** It validates *syntax* and will pass happily on a config
that cannot start. A `subnet` declaration matching no interface address is perfectly valid and
yields `No subnet declaration for <iface> (<ip>)` → `Not configured to listen on any
interfaces!` → exit 1. To prove which interfaces a *running* dhcpd actually bound, don't trust
`ss -lunp` (it shows one `0.0.0.0:67`); read the per-interface raw sockets:

```bash
sudo ss -0 -p | grep dhcpd      # one p_raw line per interface, e.g. *:eth1  *:eth3
cat /proc/net/packet            # cross-check Iface column against /sys/class/net/<if>/ifindex
```

### A client holding a lease from a subnet you stopped serving gets WEDGED, not NAK'd

dhcpd logs `unknown lease <ip>` and **sends nothing back** — `authoritative;` only makes it NAK
for subnets it knows about, and the stale address is in none of them. The client re-REQUESTs its
dead address for minutes (unicast, then broadcast REBINDING) and only recovers when the lease
fully expires. Bounce the client instead of waiting: on AW+, `no ip address dhcp` then
`ip address dhcp` on the relevant vlan.

### Two pre-existing traps in tb470's `dhcpd.conf`

- **The eth1 pool `10.38.215.2–10` overlaps the switches' static management addresses** (the
  x230's `vlan100` is statically `.2`). dhcpd's ping-check catches it — `ICMP Echo reply while
  lease 10.38.215.2 valid` → `Abandoning IP address 10.38.215.2: pinged before offer` — but
  ping-check only sees a host that answers *at that instant*, so a rebooting device can still be
  handed an address already in static use. A plausible contributor to the mgmt-IP drift in §4a.
- **`option domain-name "example.org";`** is still the Debian sample default and is handed to
  every client, which then appends it to lookups (`…weconnecttheweb.co.nz.example.org`). A
  wasted round trip per resolution, and it breaks short-name lookups.

### Packet capture on a testbox

`tcpdump` 4.99.5 and `tshark` are both installed and sudo is passwordless. Detach the capture so
the SSH call returns immediately, and bound it with `timeout` so a forgotten capture can't fill
the disk:

```bash
CAP=/tmp/eth3-cap-$(date +%Y%m%d-%H%M%S).pcap
sudo sh -c "nohup timeout 300 tcpdump -i eth3 -nn -s0 -U -w $CAP >/tmp/cap.log 2>&1 &"
# -U flushes per packet, so the file is readable WHILE the capture runs
```

Write a real pcap rather than parsing text, so one firing of a hard-to-repeat event can be
re-analysed from several angles. Reading it back:

```bash
sudo tcpdump -nn -r "$CAP" | grep -vE 'LLDP|ARP'
sudo tshark -r "$CAP" -Y dns -T fields -e frame.time -e ip.dst -e dns.qry.name \
     -e dns.flags.response -e dns.a
sudo tshark -r "$CAP" -Y tls -T fields -e tcp.srcport -e tls.record.content_type \
     -e tls.handshake.type -e tls.alert_message.desc
```

**Read the error text as a layer indicator.** `Operation timeout` meant nothing came back — the
capture held DNS queries with zero responses and **not one TCP packet**. After the fix the same
command failed with `device is disabled`, which is a *substantive answer* and therefore proof the
whole path works: you can only be told you are disabled by a server you reached, TLS-handshook
with, and submitted to. A changed error is progress; check the layer before re-debugging the
network.

Two capture-reading notes: identify the far-end device from **LLDP** in the capture
(`-Y lldp -e lldp.port.id`) rather than guessing from the MAC — a switch's L3 interface MAC need
not match the base MAC in §2. And under **TLS 1.3 the server certificate is encrypted**, so an
absent cert subject is expected, not a failure; look for `tls.alert_message` instead, and treat
`content_type 22,20` in one record as normal middlebox-compat mode.

### IDevID installs need working time first

An AW+ device installing an IDevID resolves and syncs NTP **before** it contacts the proxy,
because certificate validity windows need a real clock. It walks `pool.ntp.org` →
`time.google.com` → `time.nist.gov`, then looks up
`proxy.idevid-test.weconnecttheweb.co.nz`. A DNS or egress fault therefore surfaces as an NTP
storm first and a proxy timeout second — fix reachability, not the IDevID config.

## 5. Quick reference

| Goal | Command |
|---|---|
| Reconnect to tb105 console | `SSH_AUTH_SOCK=/run/user/1971/keyring/ssh ssh tb105` → `u5` |
| Confirm the agent has the key | `SSH_AUTH_SOCK=…/keyring/ssh ssh-add -l` |
| See how a name resolves | `ssh -G tb<NNN>` |
| Probe reachability, no login | `getent hosts tb<NNN>` · `timeout 4 bash -c 'echo > /dev/tcp/tb<NNN>/22'` |
| Non-interactive test connect | `SSH_AUTH_SOCK=…/keyring/ssh ssh -o BatchMode=yes tb<NNN> hostname` |
| Identify which unit a console is | open `/dev/uN`, send `\r`, read the **login banner** (§2) — not the prompt |
| Is a console free? | `ls /var/lock/LCK..*` · `pgrep -a minicom` · `fuser -v /dev/ttyUSBnn` |
| Is this testbox TBv4? | `ls /etc/network/interfaces` (exists ⇒ TBv4 ⇒ `Switch()` needs `/dev/uN`, not an int) |
| Run a legacy corpus script | extract from `ck.db` → staging copy + `.orig` → patch the copy → `python3` + `PYTHONPATH=/home/st-art` (§4) |
| Is a console held by an operator? | `ls /var/lock/LCK..*` (file holds the PID) · `pgrep -a minicom` · `ps -o user,tty -p <pid>` — never share a serial port (§4a) |
| Diagnose a "bugged" stack | `show stack detail` on **every** unit; `Disabled Master` + `err-disabled` ports = split stack, not a config fault (§4a) |
| Un-stack a unit | `no stackport` on 27/28, `no stack virtual-mac`, `stack <id> renumber 1`, `write`, reboot. **Never `no stack <id> enable`** — it disables all ports (§4a) |
| What media is in a port? | `show interface <port> status` → `Type` column. Not inferable from the port name; the CLI accepts speed/duplex/polarity on fibre regardless (§4a) |
| Why did `isc-dhcp-server` fail? | `sudo journalctl -u isc-dhcp-server` — **sudo required**; `dhcpd -t` only checks syntax (§4b) |
| Which interfaces did dhcpd bind? | `sudo ss -0 -p \| grep dhcpd` — one `p_raw` per interface; `ss -lunp` shows only `0.0.0.0:67` (§4b) |
| Is a lab address routable off-segment? | `dig +time=4 -b <src-addr> @1.1.1.1 pool.ntp.org` — only `10.38.215.0/24` returns; tb470 has **no NAT** (§4b) |
| Packet-capture a bench event | `sudo sh -c "nohup timeout 300 tcpdump -i <if> -nn -s0 -U -w /tmp/x.pcap &"` then `tshark -r` (§4b) |
| Client stuck on an old DHCP address | dhcpd logs `unknown lease` and sends **nothing**; bounce it: `no ip address dhcp` / `ip address dhcp` (§4b) |
| Check a script is still alive | `pgrep -f "[s]cript_name"` — bracket avoids self-match; never `pkill -f` over SSH |
| Read a framework log | `tr -d '\000' < x.log \| grep -a …` (CR line endings + embedded NULs) |
