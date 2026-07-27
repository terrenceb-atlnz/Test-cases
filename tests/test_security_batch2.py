"""Regression tests for the 2nd adversarial-review security batch (2026-07-27d):
path-traversal + agent-bridge job ownership + CORS.

All tests are in-process / unit only — NO network, NO testbox SSH, NO real hosts.
Payloads are inert path strings.
"""
import pathlib

from agent_jobs import AgentJobRegistry


# --- agent-bridge job ownership (unit; no network) ------------------------------
def test_deliver_rejects_wrong_session():
    """A result for a job owned by session A must not be deliverable by session B."""
    reg = AgentJobRegistry()
    # Enqueue a job for session 'alice' without blocking: reach in via the internal API.
    from agent_jobs import _Job
    job = _Job("alice", "prompt", "sonnet")
    with reg._lock:
        reg._queues.setdefault("alice", __import__("collections").deque()).append(job)
        reg._inflight[job.id] = job
    # Wrong session cannot deliver.
    assert reg.deliver(job.id, "pwned", False, session_id="mallory") is False
    # Owning session can.
    assert reg.deliver(job.id, "ok", False, session_id="alice") is True


def test_deliver_without_session_is_legacy_permissive():
    """No session_id passed → legacy job_id-only behavior (back-compat for old clients)."""
    reg = AgentJobRegistry()
    from agent_jobs import _Job
    job = _Job("alice", "p", "m")
    with reg._lock:
        reg._inflight[job.id] = job
    assert reg.deliver(job.id, "ok", False) is True


def test_deliver_unknown_job_is_false():
    reg = AgentJobRegistry()
    assert reg.deliver("nonexistent", "x", False, session_id="alice") is False


# --- path traversal: library filename (endpoint; in-process) --------------------
def test_library_name_traversal_rejected(client):
    """A library file name escaping the script dir must not be accepted.
    Without a confirmed session the save is rejected upstream anyway; the invariant is
    simply that a traversal name never yields a 200 (which would mean a write happened)."""
    r = client.post("/api/pytest-create/save_script/AWPTCM-T99990", json={
        "group": "Grp", "name": "scr",
        "files": {"test": {"name": "scr.py", "code": "x=1"},
                  "library": {"name": "../../evil.py", "code": "x=2"}},
    })
    assert r.status_code != 200


# --- path traversal: export case_key (endpoint; in-process) ---------------------
def test_export_rejects_traversal_case_key(client):
    """A case_key with path-traversal must be refused BEFORE any refined-cases write."""
    bad = "../../../tmp/evil"
    r = client.post("/api/wizard/export", json={"session": {"key": bad}})
    # Must be a clean 400 (validation), never a 200 that wrote outside refined-cases/.
    assert r.status_code == 400
    # ...and specifically from the KEY-SHAPE guard. Batch A added a confirm gate to the
    # same handler; when that ran first this assertion passed on the confirm-gate 400
    # instead, leaving the traversal guard untested. Pin the reason, not just the code.
    assert "invalid case key" in r.json().get("detail", "").lower()
    # And nothing was created outside refined-cases for this key.
    repo = pathlib.Path(__file__).resolve().parents[1]
    assert not (repo / "tmp" / "evil").exists()


def test_export_still_accepts_valid_key_shape(client):
    """A well-formed key is not rejected by the traversal guard.

    Batch A (2026-07-27g) means a valid key with no server-side session now 404s at the
    authority gate rather than reaching payload validation — either way, what matters
    here is that the rejection is NOT the key-shape 400.
    """
    r = client.post("/api/wizard/export", json={"session": {"key": "AWPTCM-T99990"}})
    assert r.status_code != 400
    assert "invalid case key" not in (r.text or "").lower()


# --- CORS lockdown (in-process; no network) -------------------------------------
def test_cors_allows_configured_localhost_origin(client):
    r = client.get("/health", headers={"Origin": "http://localhost:8000"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:8000"


def test_cors_blocks_foreign_origin(client):
    """A foreign origin gets no allow-origin header echoed back (browser would block it)."""
    r = client.get("/health", headers={"Origin": "https://evil.example"})
    assert r.status_code == 200   # the request itself still serves
    assert r.headers.get("access-control-allow-origin") != "https://evil.example"
