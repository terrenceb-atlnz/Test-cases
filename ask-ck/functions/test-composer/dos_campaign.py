#!/usr/bin/env python3
"""
dos_campaign.py -- one-shot AWPTCM DoS suite (T5437-T5442) for the tb470 IE520 bench.

Run AS ROOT on tb470 (so scapy and the framework console share one process):
    cd /tmp/lldp && ln -sfn /home/st-art/framework framework
    sudo -n PYTHONPATH=/home/st-art python3 dos_campaign.py [case ...]

It BUILDS UP the scenario, EXECUTES every case, and TEARS DOWN to baseline -- teardown
runs in a finally block, so a crash still cleans up. Encodes the 2026-09-03 lessons:
  * attacks must TRANSIT the switch (aimed at a host BEHIND it), never the switch's own MAC
    (CPU-punt bypasses the DoS ASIC -> 0 detections)
  * senders must be BATCHED -- single-packet sendp(loop=1) is too slow for the rate threshold
  * the Ethernet SOURCE MAC must be a VALID UNICAST -- an illegal multicast source (e.g.
    01:00:...) is dropped before any DoS counting (2026-09-04 bug; fixed: src = the sending
    NIC's own MAC).
  * disarm is `no dos <type>` (for smurf `no dos smurf`); `... action shutdown` leaves it armed
  * `dos ipoptions` on the IE520 is a CONFIRMED no-op (2026-09-28): armed it counts 0 and never
    shuts the port, on both bridged AND routed paths, with valid frames above the 20 pps
    threshold. The x230 (a platform that has the feature) detects the SAME stimulus at once. So
    ipoptions is now graded like any other case -- FAIL on the IE520, and it is a filed defect.
    See claude/device-testing/IE520/dos/5437.log.
Pass = armed+attack -> port err-disable; disarmed+attack -> port stays connected.

!! BENCH PARAMETERS BELOW ARE THE STANDING 2026-09-27 TOPOLOGY. The bench is recabled often --
   RECONCILE PORT / IFACE / VIC_* / SRC / BCAST against bench-setup/bench-state.md before every
   run (which tb NIC lands on which switch port, and the victim host behind the switch).
"""
import sys, time
from framework.Setup import LoadSetup
from scapy.all import Ether, IP, TCP, UDP, ICMP, IPOption_LSRR, sendp

# ---- bench parameters (STANDING 2026-09-27 topology -- verify vs bench-state.md) ----------
SETUP   = "/home/st-art/st-art/configs/tb470.setup"
DUT     = "swi_a"            # IE520 stack (init_swi on any member reaches the master CLI)
PORT    = "port3.0.9"       # attack ingress on the stack (member 3; faces tb470 eth3)
IFACE   = "eth3"            # tb470 NIC cabled to PORT
VIC_IP  = "10.38.215.2"     # x230 -- a host BEHIND the switch (transit victim), reached via sa2
VIC_MAC = "02:1a:eb:91:cc:a1"   # x230 as learned on the stack (sa2); NOT the switch's own MAC
SRC     = "10.38.215.90"    # a plausible source in eth3's /27 (.64/27)
BCAST   = "10.38.215.95"    # .64/27 directed broadcast (for smurf)
REACH   = ["10.38.215.10", "10.38.215.70", "10.38.215.2"]    # stack, 4050, x230
FIRE_S, NEG_S = 9, 6        # seconds to send in the positive / negative phase

def _iface_mac(ifc):
    """The sending NIC's own MAC -- a VALID UNICAST source, so frames are not dropped before
    DoS counting (the 2026-09-04 illegal-multicast-source bug). Falls back to a valid
    locally-administered unicast if the sysfs read fails."""
    try:
        return open("/sys/class/net/%s/address" % ifc).read().strip() or "02:00:00:00:00:01"
    except Exception:
        return "02:00:00:00:00:01"
SRC_MAC = _iface_mac(IFACE)

# ---- attack packet batches (same shapes as the lab tools, but batched) -------------------
def b_ipoptions(): return [Ether(dst=VIC_MAC, src=SRC_MAC)/IP(src=SRC, dst=VIC_IP, options=IPOption_LSRR(routers=[VIC_IP]))/ICMP()]*2000
def b_land():      return [Ether(src=SRC_MAC, dst=VIC_MAC)/IP(src=VIC_IP, dst=VIC_IP)/TCP(sport=80, dport=80, flags='S')]*2000
def b_pod():       return [Ether(dst=VIC_MAC, src=SRC_MAC)/IP(src=SRC, dst=VIC_IP, flags="MF", frag=8191)/ICMP(code=8)/("\x00"*1458)]*2000
def b_smurf():     return [Ether(dst="ff:ff:ff:ff:ff:ff", src=SRC_MAC)/IP(src=SRC, dst=BCAST)/ICMP(code=8)]*2000
def b_synflood():  return [Ether(src=SRC_MAC, dst=VIC_MAC)/IP(src=SRC, dst=VIC_IP)/TCP(sport=1024+(i*37) % 64000, dport=80, flags='S') for i in range(2000)]
def b_teardrop():
    """Overlapping-fragment train: frag0 (MF), 10 stepped MF frags, one final non-MF frag."""
    load = "\x00"*800
    base = Ether(dst=VIC_MAC, src=SRC_MAC)/IP(dst=VIC_IP, src=SRC, proto=17, flags="MF")/UDP(dport=80)
    train, off = [base/load], 3
    for _ in range(10):
        f = base.copy(); f.frag = off; off += 20; train.append(f/load)
    last = base.copy(); last.flags = 0; last.frag = off; train.append(last/load)
    return train*160     # ~1900 pkts/batch to keep the send rate up

#           key           arm-cli                                              disarm-cli                    builder      exercisable
CASES = [
 ("ipoptions",     "dos ipoptions action shutdown",                     "no dos ipoptions",             b_ipoptions, True ),
 ("land",          "dos land action shutdown",                          "no dos land",                  b_land,      True ),
 ("ping-of-death", "dos ping-of-death action shutdown",                 "no dos ping-of-death",         b_pod,       True ),
 ("smurf",         "dos smurf broadcast %s action shutdown" % BCAST,    "no dos smurf",                 b_smurf,     True ),
 ("synflood",      "dos synflood action shutdown",                      "no dos synflood",              b_synflood,  True ),
 ("teardrop",      "dos teardrop action shutdown",                      "no dos teardrop",              b_teardrop,  True ),
]
ALL_DISARM = [c[2] for c in CASES]

# ---- framework console helpers ----------------------------------------------------------
def cfg(dev, lines):
    dev.mode(')#')
    for l in lines:
        dev.cmd(l)
    dev.mode('#')

def sh(dev, cmd):
    dev.mode('#')
    return dev.cmd(cmd)

def port_state(dev):
    """Return 'connected' / 'err-disable' / other for PORT."""
    for ln in sh(dev, "show interface %s status" % PORT).splitlines():
        if ln.strip().startswith(PORT):
            return "err-disable" if "err-disable" in ln else ("connected" if "connected" in ln else "down")
    return "?"

def wait_connected(dev, timeout=30):
    """Poll until PORT is forwarding again -- an err-disable recovery or link-up is not
    instant, and firing into a settling port drops packets below the detection threshold."""
    end = time.time() + timeout
    while time.time() < end:
        if port_state(dev) == "connected":
            return True
        time.sleep(2)
    return False

def fire(builder, seconds):
    """Batched, time-bounded transit attack. Returns approx packets sent."""
    batch, n, end = builder(), 0, time.time() + seconds
    while time.time() < end:
        sendp(batch, iface=IFACE, verbose=0)
        n += len(batch)
    return n

def ping_all():
    import subprocess
    up = []
    for ip in REACH:
        ok = subprocess.run(["ping", "-c2", "-W1", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        up.append("%s %s" % (ip, "UP" if ok else "DOWN"))
    return up

# ---- phases -----------------------------------------------------------------------------
def build_up(dut):
    print("== BUILD-UP ==", flush=True)
    cfg(dut, ["interface %s" % PORT, "no shutdown"] + ALL_DISARM)   # clean slate
    wait_connected(dut)
    print("  port %s: %s" % (PORT, port_state(dut)))
    print("  reachability: " + " | ".join(ping_all()))
    if port_state(dut) != "connected":
        raise SystemExit("build-up: %s not connected -- aborting" % PORT)

def run_case(dut, key, arm, disarm, builder, exercisable):
    print("\n== %s ==" % key.upper(), flush=True)
    cfg(dut, ["interface %s" % PORT, "no shutdown"]); wait_connected(dut)
    cfg(dut, ["interface %s" % PORT, arm])
    sent = fire(builder, FIRE_S); time.sleep(3)
    st = port_state(dut)
    if exercisable and st != "err-disable":           # retry once -- absorb rate/timing variance
        cfg(dut, ["interface %s" % PORT, "no shutdown"]); wait_connected(dut)
        sent += fire(builder, FIRE_S); time.sleep(3)
        st = port_state(dut)
    print("  armed + attack (~%d pkts): port -> %s" % (sent, st))
    cfg(dut, ["interface %s" % PORT, "no shutdown", disarm]); wait_connected(dut)
    fire(builder, NEG_S); time.sleep(3)
    neg = port_state(dut)
    print("  disarmed + attack: port -> %s" % neg)
    if exercisable:
        # PASS only if arming detected (port shut) AND disarming stopped detecting (port stayed up).
        # Armed-but-no-detection is a FAIL -- this is what caught the IE520 ipoptions defect.
        verdict = "PASS" if (st == "err-disable" and neg == "connected") else "FAIL"
    else:
        verdict = "SKIPPED (marked not exercisable on this bench)"
    print("  verdict: %s" % verdict)
    return verdict

def teardown(dut):
    print("\n== TEARDOWN ==", flush=True)
    cfg(dut, ["interface %s" % PORT, "no shutdown"] + ALL_DISARM)
    time.sleep(5)
    left = [ln.strip() for ln in sh(dut, "show running-config interface %s" % PORT).splitlines() if "dos " in ln]
    print("  residual dos config: %s" % (left or "none"))
    print("  port %s: %s" % (PORT, port_state(dut)))
    print("  reachability: " + " | ".join(ping_all()))

# ---- main -------------------------------------------------------------------------------
def main():
    want = set(a.replace("_", "-") for a in sys.argv[1:])
    cases = [c for c in CASES if not want or c[0] in want]
    setup = LoadSetup(SETUP)
    dut = setup.init_swi(DUT, powerOn=False); dut.console.mode('#')
    results = {}
    try:
        build_up(dut)
        for key, arm, disarm, builder, ex in cases:
            results[key] = run_case(dut, key, arm, disarm, builder, ex)
    finally:
        teardown(dut)
    print("\n== SUMMARY ==")
    for k in [c[0] for c in cases]:
        print("  %-14s %s" % (k, results.get(k, "not run")))

if __name__ == "__main__":
    main()
