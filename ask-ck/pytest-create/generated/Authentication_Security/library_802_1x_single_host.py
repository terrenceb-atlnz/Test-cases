#!/usr/bin/python3
# Helper library for AWPTCM-T33351 — 802.1X single-host supplicant emulation and parsing.
# Adapted from ART 1367_security_failover/library_1367.py (status parser) and the legacy
# tools/auth_simulator/dot1x_simulator.py (scapy supplicant driver). Runs on the testbox
# python3 (3.13) — stdlib only besides scapy, which the corpus already depends on.

import time
import hashlib

from scapy.all import Ether, ARP, sendp, AsyncSniffer

try:
    from scapy.layers.eap import EAPOL, EAP, EAP_MD5
    _HAVE_MD5 = True
except Exception:
    try:
        from scapy.layers.eap import EAPOL, EAP
    except Exception:
        from scapy.all import EAPOL, EAP
    EAP_MD5 = None
    _HAVE_MD5 = False

EAP_GROUP_MAC = '01:80:c2:00:00:03'


def getLine(output, token):
    for line in output.split('\n'):
        if token in line:
            return line
    return ''


def mac_variants(mac):
    """Return the MAC in the formats AW+ show commands may print it in."""
    m = mac.lower().replace(':', '').replace('-', '').replace('.', '')
    colon = ':'.join(m[i:i + 2] for i in range(0, 12, 2))
    dash = '-'.join(m[i:i + 2] for i in range(0, 12, 2))
    cisco = '.'.join(m[i:i + 4] for i in range(0, 12, 4))
    return [colon, dash, cisco, m]


def find_supp_line(output, mac):
    variants = mac_variants(mac)
    for line in output.split('\n'):
        low = line.lower()
        for v in variants:
            if v in low:
                return line
    return None


def make_arp_frame(src_mac, src_ip, dst_ip):
    return Ether(src=src_mac, dst='ff:ff:ff:ff:ff:ff') / ARP(
        op=1, hwsrc=src_mac, psrc=src_ip, pdst=dst_ip)


def send_and_capture(tx_iface, rx_iface, pkt, bpf=None, count=3, settle=1.5, timeout=4):
    """Send `pkt` on tx_iface while sniffing rx_iface; return the captured packet list."""
    sniffer = AsyncSniffer(iface=rx_iface, filter=bpf, store=True)
    sniffer.start()
    time.sleep(settle)
    sendp(pkt, iface=tx_iface, count=count, inter=0.2, verbose=False)
    time.sleep(timeout)
    try:
        pkts = sniffer.stop()
    except Exception:
        pkts = []
    return list(pkts or [])


def send_eapol_start(iface, src_mac):
    pkt = Ether(src=src_mac, dst=EAP_GROUP_MAC, type=0x888e) / EAPOL(version=2, type=1)
    sendp(pkt, iface=iface, verbose=False)


def send_eapol_logoff(iface, src_mac):
    pkt = Ether(src=src_mac, dst=EAP_GROUP_MAC, type=0x888e) / EAPOL(version=2, type=2)
    sendp(pkt, iface=iface, verbose=False)


def run_dot1x_authenticate(testCase, iface, src_mac, username, password, timeout=20):
    """Best-effort EAP-MD5 supplicant driven with scapy.

    Sends EAPOL-Start, answers EAP Request/Identity and (where scapy exposes EAP_MD5) an
    EAP-MD5 challenge, and returns True on EAP-Success, False otherwise. The caller's real
    verdict is taken from the DUT's show output; this just drives the exchange.
    """
    sniffer = AsyncSniffer(iface=iface, filter='ether proto 0x888e', store=True)
    sniffer.start()
    time.sleep(0.5)
    send_eapol_start(iface, src_mac)
    deadline = time.time() + timeout
    result = False
    seen = set()
    while time.time() < deadline:
        time.sleep(1)
        pkts = sniffer.stop()
        sniffer = AsyncSniffer(iface=iface, filter='ether proto 0x888e', store=True)
        sniffer.start()
        for p in (pkts or []):
            if not p.haslayer(EAP):
                continue
            eap = p[EAP]
            key = (int(eap.code), int(getattr(eap, 'id', 0)), int(getattr(eap, 'type', 0)))
            if key in seen:
                continue
            seen.add(key)
            if eap.code == 3:
                testCase.log('dot1x supplicant received EAP-Success')
                try:
                    sniffer.stop()
                except Exception:
                    pass
                return True
            if eap.code == 4:
                testCase.log('dot1x supplicant received EAP-Failure')
                continue
            if eap.code == 1:
                if eap.type == 1:
                    resp = (Ether(src=src_mac, dst=EAP_GROUP_MAC, type=0x888e)
                            / EAPOL(version=2, type=0)
                            / EAP(code=2, id=eap.id, type=1, identity=username.encode()))
                    sendp(resp, iface=iface, verbose=False)
                elif eap.type == 4 and _HAVE_MD5 and p.haslayer(EAP_MD5):
                    md5 = p[EAP_MD5]
                    challenge = bytes(md5.value)
                    digest = hashlib.md5(
                        bytes([int(md5.id)]) + password.encode() + challenge).digest()
                    resp = (Ether(src=src_mac, dst=EAP_GROUP_MAC, type=0x888e)
                            / EAPOL(version=2, type=0)
                            / EAP_MD5(code=2, id=md5.id, type=4,
                                      value_size=len(digest), value=digest,
                                      optional_name=username.encode()))
                    sendp(resp, iface=iface, verbose=False)
    try:
        sniffer.stop()
    except Exception:
        pass
    return result
