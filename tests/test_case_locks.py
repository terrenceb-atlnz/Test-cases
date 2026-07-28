"""Case locking — Phase 1 (PLAN-auth-and-case-locking.md).

Covers the in-memory lock registry, the persist-time write guard + rev optimistic
backstop, and the HTTP surface end-to-end. All keys are in the reserved throwaway block
(AWPTCM-T99980..T99999) so nothing here can touch a real session even if isolation broke.
"""
from datetime import datetime, timedelta, timezone

import pytest

import db
import locks
import session_store
from models import WizardSession

K = "AWPTCM-T99996"
K2 = "AWPTCM-T99997"
K3 = "AWPTCM-T99998"


@pytest.fixture(autouse=True)
def _clean_locks():
    locks._reset()
    yield
    locks._reset()


class _Clock:
    """A controllable stand-in for locks.utc_now so expiry is tested without sleeping."""
    def __init__(self, start):
        self.now = start
    def __call__(self):
        return self.now
    def advance(self, secs):
        self.now = self.now + timedelta(seconds=secs)


def _clock(monkeypatch):
    clk = _Clock(datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc))
    monkeypatch.setattr(locks, "utc_now", clk)
    return clk


# --- registry semantics ------------------------------------------------------

def test_acquire_grants_when_free():
    s = locks.acquire("wizard", K, holder="A", label="Alice")
    assert s["held"] and s["by_me"] and s["acquired"]
    assert s["holder"] == "A" and s["holder_label"] == "Alice"


def test_second_holder_is_refused_not_granted():
    locks.acquire("wizard", K, holder="A", label="Alice")
    s = locks.acquire("wizard", K, holder="B")
    assert s["held"] and not s["by_me"] and not s["acquired"]
    assert s["holder"] == "A" and s["holder_label"] == "Alice"


def test_same_holder_reacquire_keeps_since_but_refreshes_heartbeat(monkeypatch):
    clk = _clock(monkeypatch)
    s1 = locks.acquire("wizard", K, holder="A")
    clk.advance(90)
    s2 = locks.acquire("wizard", K, holder="A")
    assert s2["by_me"]
    assert s2["acquired_at"] == s1["acquired_at"], "held-since must stay stable on refresh"
    assert s2["heartbeat_at"] != s1["heartbeat_at"], "heartbeat must advance"


def test_require_can_write_rules():
    locks.require_can_write("wizard", K, holder="A")          # no lock -> allowed
    locks.acquire("wizard", K, holder="A")
    locks.require_can_write("wizard", K, holder="A")          # mine -> allowed
    with pytest.raises(locks.LockConflictError):
        locks.require_can_write("wizard", K, holder="B")      # someone else -> 409


def test_expiry_makes_lock_stealable_and_writable(monkeypatch):
    clk = _clock(monkeypatch)
    locks.acquire("wizard", K, holder="A")
    clk.advance(locks.LOCK_IDLE_TTL + 1)
    st = locks.peek("wizard", K, holder="B")
    assert st["held"] and st["expired"] and st["stealable"] and not st["by_me"]
    locks.require_can_write("wizard", K, holder="B")          # abandoned -> allowed
    s = locks.acquire("wizard", K, holder="B")                # B takes it over
    assert s["by_me"] and s["holder"] == "B"


def test_heartbeat_prevents_expiry(monkeypatch):
    clk = _clock(monkeypatch)
    locks.acquire("wizard", K, holder="A")
    clk.advance(locks.LOCK_IDLE_TTL - 1)
    locks.heartbeat("wizard", K, holder="A")                  # reset the idle timer
    clk.advance(locks.LOCK_IDLE_TTL - 1)                      # > TTL since acquire, < TTL since beat
    st = locks.peek("wizard", K, holder="A")
    assert st["by_me"] and not st["expired"]


def test_heartbeat_and_release_by_nonholder_are_noops():
    locks.acquire("wizard", K, holder="A")
    assert locks.heartbeat("wizard", K, holder="B")["holder"] == "A"
    r = locks.release("wizard", K, holder="B")
    assert r["released"] is False and r["held"] is True


def test_release_by_holder_frees_the_lock():
    locks.acquire("wizard", K, holder="A")
    r = locks.release("wizard", K, holder="A")
    assert r["released"] is True and r["held"] is False
    assert not locks.peek("wizard", K, holder="B")["held"]


def test_wizard_and_pt_lock_the_same_case_independently():
    locks.acquire("wizard", K, holder="A")
    s = locks.acquire("pt", K, holder="B")     # different tool -> separate lock (D3)
    assert s["by_me"] and s["holder"] == "B"


# --- rev optimistic backstop (next_rev) --------------------------------------

def test_next_rev_bumps_when_in_sync(monkeypatch):
    monkeypatch.setattr(db, "load_session", lambda kind, key: {"rev": 5})
    assert locks.next_rev("wizard", K, 5) == 6


def test_next_rev_raises_when_superseded(monkeypatch):
    monkeypatch.setattr(db, "load_session", lambda kind, key: {"rev": 7})
    with pytest.raises(locks.StaleWriteError):
        locks.next_rev("wizard", K, 5)


def test_next_rev_first_write_and_legacy_rowless(monkeypatch):
    monkeypatch.setattr(db, "load_session", lambda kind, key: None)
    assert locks.next_rev("wizard", K, 0) == 1                 # no row yet
    monkeypatch.setattr(db, "load_session", lambda kind, key: {"key": K})
    assert locks.next_rev("wizard", K, 0) == 1                 # legacy row, no rev key


def test_next_rev_read_failure_does_not_masquerade_as_conflict(monkeypatch):
    def boom(kind, key):
        raise RuntimeError("db down")
    monkeypatch.setattr(db, "load_session", boom)
    assert locks.next_rev("wizard", K, 3) == 4                 # let the write path surface real errors


def test_lock_errors_share_a_base():
    assert issubclass(locks.LockConflictError, locks.LockError)
    assert issubclass(locks.StaleWriteError, locks.LockError)


# --- persist choke point (guard runs before any DB write) --------------------

def test_persist_blocked_when_another_holds_and_never_writes(monkeypatch):
    locks.acquire("wizard", K, holder="other")     # current_holder() is '' here != 'other'
    wrote = {"n": 0}
    monkeypatch.setattr(db, "load_session", lambda *a, **k: None)
    monkeypatch.setattr(db, "save_session", lambda *a, **k: wrote.__setitem__("n", wrote["n"] + 1))
    with pytest.raises(locks.LockConflictError):
        session_store.persist_session(WizardSession(key=K))
    assert wrote["n"] == 0, "the write must be refused BEFORE reaching the DB"


def test_persist_allowed_for_holder_and_bumps_rev(monkeypatch):
    locks.acquire("wizard", K, holder="")          # '' == the test's current_holder()
    store = {"rev": 0}
    monkeypatch.setattr(db, "load_session", lambda kind, key: {"rev": store["rev"]})
    monkeypatch.setattr(db, "save_session", lambda kind, key, data: store.__setitem__("rev", data["rev"]))
    sess = WizardSession(key=K)
    session_store.persist_session(sess)
    assert sess.rev == 1 and store["rev"] == 1
    session_store.persist_session(sess)
    assert sess.rev == 2 and store["rev"] == 2


# --- HTTP surface ------------------------------------------------------------

def test_lock_endpoints_round_trip(client):
    a = {"X-CK-Session": "A"}
    b = {"X-CK-Session": "B"}
    r = client.post(f"/api/locks/wizard/{K}/acquire", headers=a)
    assert r.status_code == 200 and r.json()["by_me"] is True and r.json()["acquired"] is True
    j = client.get(f"/api/locks/wizard/{K}", headers=b).json()
    assert j["held"] and not j["by_me"] and j["holder"] == "A"
    assert client.post(f"/api/locks/wizard/{K}/acquire", headers=b).json()["by_me"] is False
    assert client.post(f"/api/locks/wizard/{K}/heartbeat", headers=a).json()["by_me"] is True
    assert client.post(f"/api/locks/wizard/{K}/release", headers=b).json()["released"] is False
    assert client.post(f"/api/locks/wizard/{K}/release", headers=a).json()["released"] is True
    assert client.get(f"/api/locks/wizard/{K}", headers=a).json()["held"] is False


def test_lock_unknown_kind_is_400(client):
    assert client.post(f"/api/locks/bogus/{K}/acquire", headers={"X-CK-Session": "A"}).status_code == 400


def test_beacon_release_carries_holder_in_body(client):
    # navigator.sendBeacon cannot set X-CK-Session; the holder rides in the JSON body.
    client.post(f"/api/locks/pt/{K2}/acquire", headers={"X-CK-Session": "A"})
    r = client.post(f"/api/locks/pt/{K2}/release", headers={"X-CK-Session": "B"}, json={"holder": "A"})
    assert r.json()["released"] is True


def test_write_by_nonholder_is_409_through_the_app(client):
    from routers.pytest_create import pt_sessions
    from models import PtSession
    pt_sessions[K3] = PtSession(key=K3, step3={"matches": [], "provenance": {"model": "t"}})
    try:
        locks.acquire("pt", K3, holder="other")
        r = client.post(f"/api/pytest-create/confirm_step/{K3}/3",
                        headers={"X-CK-Session": "me"}, json={})
        assert r.status_code == 409
        assert "locked" in r.json()["detail"].lower() or "being edited" in r.json()["detail"].lower()
    finally:
        pt_sessions.pop(K3, None)


def test_pt_load_case_is_readonly_when_locked_by_another(client):
    from routers.pytest_create import pt_sessions
    pt_sessions.pop(K2, None)
    locks.acquire("pt", K2, holder="other")
    j = client.post(f"/api/pytest-create/load_case/{K2}", headers={"X-CK-Session": "me"}).json()
    assert j["read_only"] is True
    assert j["lock"]["by_me"] is False and j["lock"]["holder"] == "other"
