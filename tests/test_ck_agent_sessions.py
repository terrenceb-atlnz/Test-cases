"""ck-agent's agent sessions (ask-ck/plans/PLAN-agent-sessions.md P1, D6/D7).

A session is a full-tools, long-lived Claude Code session the page starts on the seat: it runs
device-testing's /test-mode --from-ask-ck in the seat's own device-testing checkout, through the
Claude Agent SDK, with the D6 permission profile. These drive the REAL session code against a FAKE
SDK (the module seam `_sdk_loader`), so no seat is spent. What they pin:

  * the page never chooses a directory, a settings file or the prompt's command: the agent builds
    `/test-mode --from-ask-ck <its own hand-off copy> <case keys>`, from its own config;
  * no device-testing checkout with the profile, or no SDK → no session, and /health says why;
  * campaigns never wait for an answer (D5): a question is denied at once with the D5 reply;
    an interactive session waits up to its timeout and passes the page's answers through;
  * RESULT / NOTIFY / ASKCK-DONE lines become marker events; ASKCK-DONE ends the session;
  * the HTTP routes are JSON-only (a cross-site simple POST cannot start a full-tools session).
"""
import asyncio
import http.client
import json
import sys
import threading
import time
import types
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "ask-ck" / "agent"))

import ck_agent  # noqa: E402


# ---------------------------------------------------------------- a fake Agent SDK

class TextBlock:
    def __init__(self, text): self.text = text
class ToolUseBlock:
    def __init__(self, id, name, input): self.id, self.name, self.input = id, name, input
class ThinkingBlock:
    def __init__(self, thinking, signature="sig"): self.thinking, self.signature = thinking, signature
class ToolResultBlock:
    def __init__(self, tool_use_id, content, is_error=False):
        self.tool_use_id, self.content, self.is_error = tool_use_id, content, is_error
class AssistantMessage:
    def __init__(self, content, parent=None): self.content, self.parent_tool_use_id = content, parent
class UserMessage:
    def __init__(self, content, parent=None): self.content, self.parent_tool_use_id = content, parent
class SystemMessage:
    def __init__(self, subtype, data): self.subtype, self.data = subtype, data
class ResultMessage:
    def __init__(self, result, cost=0.5):
        self.subtype, self.is_error, self.num_turns, self.duration_ms = "success", False, 3, 1200
        self.total_cost_usd, self.usage, self.model_usage, self.result = cost, {"output_tokens": 10}, {"m": {"costUSD": cost}}, result
class PermissionResultAllow:
    def __init__(self, updated_input=None): self.updated_input = updated_input
class PermissionResultDeny:
    def __init__(self, message=""): self.message = message
class ClaudeAgentOptions:
    def __init__(self, **kw): self.__dict__.update(kw)


def fake_sdk(script):
    """`script(client)` is an async generator of messages for the first query; it may call
    `await client.ask(tool, input)` to go through the session's can_use_tool."""
    state = {"queries": [], "options": None, "interrupted": False}

    class ClaudeSDKClient:
        def __init__(self, options):
            self.options = options
            state["options"] = options
            self._queue = asyncio.Queue()
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def query(self, prompt):
            state["queries"].append(prompt)
            if len(state["queries"]) == 1:
                async def run():
                    async for m in script(self):
                        await self._queue.put(m)
                asyncio.ensure_future(run())
            else:
                await self._queue.put(AssistantMessage([TextBlock("ack: " + prompt)]))
        async def ask(self, tool, inp):
            return await self.options.can_use_tool(tool, inp, None)
        async def interrupt(self):
            state["interrupted"] = True
            await self._queue.put(None)
        async def receive_messages(self):
            while True:
                m = await self._queue.get()
                if m is None:
                    return
                yield m

    mod = types.SimpleNamespace(ClaudeSDKClient=ClaudeSDKClient, ClaudeAgentOptions=ClaudeAgentOptions,
                                PermissionResultAllow=PermissionResultAllow, PermissionResultDeny=PermissionResultDeny,
                                __version__="0.0.test")
    return mod, state


@pytest.fixture
def dt(tmp_path, monkeypatch):
    root = tmp_path / "device-testing"
    (root / ".claude").mkdir(parents=True)
    (root / ".claude" / "ask-ck-campaign.settings.json").write_text("{}")
    monkeypatch.setenv("CK_DT_ROOT", str(root))
    monkeypatch.setenv("CK_AGENT_RUNS", str(tmp_path / "runs"))
    monkeypatch.setattr(ck_agent, "_find_claude", lambda: "/usr/bin/claude")
    ck_agent._SESSIONS.clear()
    yield root
    for s in list(ck_agent._SESSIONS.values()):
        s.stop()
    ck_agent._SESSIONS.clear()


def use(monkeypatch, script):
    mod, state = fake_sdk(script)
    monkeypatch.setattr(ck_agent, "_sdk_loader", lambda: mod)
    return state


HANDOFF = {"schema": 1, "run_id": "r1", "kind": "validation", "testbox": "tb470",
           "cases": [{"key": "AWPTCM-T33234", "kind": "script"}, {"key": "bad key; rm -rf", "kind": "script"}]}


def wait_state(s, states, timeout=5):
    t0 = time.time()
    while s.state not in states and time.time() - t0 < timeout:
        time.sleep(0.02)
    assert s.state in states, (s.state, s.error, [e["kind"] for e in s.events])


async def _campaign(client):
    yield SystemMessage("init", {"session_id": "S", "model": "opus", "permissionMode": "auto", "cwd": "x"})
    yield AssistantMessage([TextBlock("Starting triage."),
                            ToolUseBlock("t1", "Bash", {"command": "tools/tb precheck tb470 0-5", "description": "precheck"})])
    yield UserMessage([ToolResultBlock("t1", "CLEAR")])
    verdict = await client.ask("AskUserQuestion", {"questions": [{"question": "Which PDU?", "options": []}]})
    yield AssistantMessage([TextBlock(f"question answered: {type(verdict).__name__}: {getattr(verdict, 'message', '')[:40]}")])
    yield UserMessage([ToolResultBlock("t2", "Permission for this action was denied by the Claude Code auto mode classifier.", True)])
    yield SystemMessage("task_started", {"task_id": "a1", "description": "triage", "subagent_type": "bench-runner", "is_backgrounded": True})
    yield SystemMessage("task_notification", {"task_id": "a1", "status": "completed", "summary": "done", "usage": {"total_tokens": 99}})
    yield AssistantMessage([TextBlock("RESULT AWPTCM-T33234 UNSUPPORTED -- no copper port -- work/run1.log\n"
                                      "NOTIFY campaign -- consoles logged in -- left them")])
    yield ResultMessage("Triage done.")
    yield AssistantMessage([TextBlock("`ASKCK-DONE r1`")])
    yield ResultMessage("Stood down.", cost=2.75)    # the turn's result: the session's FINAL cost


# ---------------------------------------------------------------- capability and refusals

def test_no_sdk_means_no_session_and_health_says_why(dt, monkeypatch):
    def boom():
        raise ImportError("no claude_agent_sdk")
    monkeypatch.setattr(ck_agent, "_sdk_loader", boom)
    cap = ck_agent.session_capability()
    assert cap["available"] is False and "SDK not installed" in cap["reason"]
    assert ck_agent.start_session({"run_id": "r1", "handoff": HANDOFF})["ok"] is False


def test_no_permission_profile_means_no_session(dt, monkeypatch):
    use(monkeypatch, _campaign)
    (dt / ".claude" / "ask-ck-campaign.settings.json").unlink()
    r = ck_agent.start_session({"run_id": "r1", "handoff": HANDOFF})
    assert r["ok"] is False and "permission profile" in r["error"]


def test_the_run_id_must_be_well_formed_and_match_the_handoff(dt, monkeypatch):
    use(monkeypatch, _campaign)
    assert ck_agent.start_session({"run_id": "../etc", "handoff": HANDOFF})["ok"] is False
    # a path escape is refused even when the hand-off agrees with it (it becomes a directory name)
    for bad in ("../etc", "a/b", "", ".hidden"):
        assert ck_agent.start_session({"run_id": bad, "handoff": dict(HANDOFF, run_id=bad)})["ok"] is False, bad
    assert ck_agent.start_session({"run_id": "r2", "handoff": HANDOFF})["ok"] is False


# ---------------------------------------------------------------- a campaign end to end

def test_a_campaign_runs_test_mode_in_the_checkout_with_the_profile_and_ends_on_askck_done(dt, monkeypatch):
    state = use(monkeypatch, _campaign)
    r = ck_agent.start_session({"run_id": "r1", "handoff": HANDOFF, "cwd": "/etc", "prompt": "rm -rf /"})
    assert r["ok"], r
    s = ck_agent.get_session(r["session_id"])
    wait_state(s, ("done", "error", "stopped"))
    assert s.state == "done", s.error
    o = state["options"]
    assert o.cwd == str(dt)
    assert o.settings == str(dt / ".claude" / "ask-ck-campaign.settings.json")
    assert o.permission_mode == "auto" and o.cli_path == "/usr/bin/claude"
    hp = Path(s.handoff_path)
    assert hp.name == "r1.json"            # /test-mode's stopgap reads the run id from the basename
    # the hand-off as sent, plus where the sentinel's updates go (also in the session's env)
    assert json.loads(hp.read_text()) == dict(HANDOFF, sentinel_updates=s.updates_path)
    assert Path(s.updates_path).parent == hp.parent
    assert o.env == {"CK_SENTINEL_UPDATES": s.updates_path}
    # the agent builds the command; the page's cwd/prompt fields are ignored; bad keys dropped
    assert state["queries"][0] == f"/test-mode --from-ask-ck {hp} AWPTCM-T33234"
    kinds = [e["kind"] for e in s.events]
    for k in ("state", "init", "text", "tool_use", "tool_result", "question", "answered", "task", "marker", "result"):
        assert k in kinds, k
    markers = [e["line"] for e in s.events if e["kind"] == "marker"]
    assert markers == ["RESULT AWPTCM-T33234 UNSUPPORTED -- no copper port -- work/run1.log",
                       "NOTIFY campaign -- consoles logged in -- left them", "ASKCK-DONE r1"]
    denied = [e for e in s.events if e["kind"] == "tool_result" and e["denied"]]
    assert len(denied) == 1
    res = [e for e in s.events if e["kind"] == "result"][0]
    assert res["total_cost_usd"] == 0.5
    assert [e["seq"] for e in s.events] == list(range(len(s.events)))
    assert (Path(s.dir) / "events.jsonl").read_text().count("\n") == len(s.events)


def test_a_campaign_never_waits_for_an_answer(dt, monkeypatch):
    use(monkeypatch, _campaign)
    s = ck_agent.get_session(ck_agent.start_session({"run_id": "r1", "handoff": HANDOFF})["session_id"])
    wait_state(s, ("done",))
    said = [e["text"] for e in s.events if e["kind"] == "text" and "question answered" in e["text"]][0]
    assert "PermissionResultDeny" in said and "Ask-CK campaign" in said
    assert [e["by"] for e in s.events if e["kind"] == "answered"] == ["nobody"]


def test_an_interactive_session_waits_and_passes_the_pages_answer_through(dt, monkeypatch):
    got = {}

    async def script(client):
        verdict = await client.ask("AskUserQuestion", {"questions": [{"question": "Which PDU?"}]})
        got["v"] = verdict
        yield AssistantMessage([TextBlock("ASKCK-DONE r1")])
        yield ResultMessage("done")

    use(monkeypatch, script)
    s = ck_agent.get_session(ck_agent.start_session(
        {"run_id": "r1", "handoff": HANDOFF, "mode": "interactive", "question_timeout": 30})["session_id"])
    t0 = time.time()
    while not s.pending and time.time() - t0 < 5:
        time.sleep(0.02)
    rid = next(iter(s.pending))
    assert ck_agent.session_post(f"/session/{s.id}/answer", {"request_id": rid, "answers": {"Which PDU?": "10.36.150.14"}})["ok"]
    wait_state(s, ("done",))
    assert type(got["v"]).__name__ == "PermissionResultAllow"
    assert got["v"].updated_input["answers"] == {"Which PDU?": "10.36.150.14"}


def test_a_message_from_the_page_is_sent_into_the_session(dt, monkeypatch):
    async def script(client):
        yield SystemMessage("init", {})
        await asyncio.sleep(0.4)          # stay alive long enough to receive the page's message

    state = use(monkeypatch, script)
    s = ck_agent.get_session(ck_agent.start_session({"run_id": "r1", "handoff": HANDOFF})["session_id"])
    wait_state(s, ("running",))
    assert ck_agent.session_post(f"/session/{s.id}/message", {"text": "don't touch u3"})["ok"]
    t0 = time.time()
    while len(state["queries"]) < 2 and time.time() - t0 < 5:
        time.sleep(0.02)
    assert state["queries"][1] == "don't touch u3"
    ck_agent.session_post(f"/session/{s.id}/stop", {})
    wait_state(s, ("stopped", "done"))


def test_stop_interrupts_the_session(dt, monkeypatch):
    async def script(client):
        yield SystemMessage("init", {})
        await asyncio.sleep(30)

    state = use(monkeypatch, script)
    s = ck_agent.get_session(ck_agent.start_session({"run_id": "r1", "handoff": HANDOFF})["session_id"])
    wait_state(s, ("running",))
    s.stop()
    wait_state(s, ("stopped",))
    assert state["interrupted"] is True


def test_starting_the_same_run_twice_returns_the_running_session(dt, monkeypatch):
    async def script(client):
        yield SystemMessage("init", {})
        await asyncio.sleep(30)

    use(monkeypatch, script)
    a = ck_agent.start_session({"run_id": "r1", "handoff": HANDOFF})
    b = ck_agent.start_session({"run_id": "r1", "handoff": HANDOFF})
    assert b["already"] is True and b["session_id"] == a["session_id"]


# ---------------------------------------------------------------- HTTP

@pytest.fixture
def server(dt):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), ck_agent.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield httpd.server_address[1]
    httpd.shutdown()


def _req(port, method, path, body=None, ctype="application/json"):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    data = json.dumps(body).encode() if body is not None else None
    c.request(method, path, body=data, headers={"Content-Type": ctype} if data else {})
    r = c.getresponse()
    return r.status, json.loads(r.read() or b"{}")


def test_the_routes_start_long_poll_and_stop_a_session_json_only(server, monkeypatch):
    use(monkeypatch, _campaign)
    assert _req(server, "POST", "/session/start", {"run_id": "r1", "handoff": HANDOFF}, ctype="text/plain")[0] == 415
    code, r = _req(server, "POST", "/session/start", {"run_id": "r1", "handoff": HANDOFF})
    assert code == 200 and r["ok"], r
    sid, after, kinds, state = r["session_id"], 0, [], None
    for _ in range(50):
        code, ev = _req(server, "GET", f"/session/{sid}/events?after={after}&wait=1")
        kinds += [e["kind"] for e in ev["events"]]
        after, state = ev["next"], ev["state"]
        if state in ("done", "error", "stopped"):
            break
    assert state == "done" and "marker" in kinds
    assert _req(server, "GET", "/session/nope/events")[0] == 404
    code, lst = _req(server, "GET", "/sessions")
    assert [x["run_id"] for x in lst["sessions"]] == ["r1"]
    assert _req(server, "POST", f"/session/{sid}/message", {"text": "hi"})[1]["ok"] is False   # session ended


def test_health_reports_session_capability(dt, monkeypatch):
    use(monkeypatch, _campaign)
    monkeypatch.setattr(ck_agent, "_find_claude", lambda: None)
    h = ck_agent.health_payload()
    assert h["sessions"]["available"] is True and h["sessions"]["sdk_version"] == "0.0.test"


# ---------------------------------------------------------------- where the session runs

@pytest.fixture
def seat(tmp_path, monkeypatch):
    """A seat with no explicit dt_root: HOME is a temp dir, the agent's conf names only the server."""
    monkeypatch.delenv("CK_DT_ROOT", raising=False)
    monkeypatch.delenv("CK_AGENT_ORIGIN", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(ck_agent, "_CONF", {"origin": "http://srv:8000"})
    monkeypatch.setattr(ck_agent, "_SERVER_DT", {"at": None, "path": None})
    fetched = []
    state = {"reply": {}}

    def fetch(origin):
        fetched.append(origin)
        if isinstance(state["reply"], Exception):
            raise state["reply"]
        return state["reply"]
    monkeypatch.setattr(ck_agent, "_fetch_server_status", fetch)
    return types.SimpleNamespace(tmp=tmp_path, fetched=fetched, state=state)


def _checkout(path):
    (path / ".claude").mkdir(parents=True)
    (path / ".claude" / "ask-ck-campaign.settings.json").write_text("{}")
    return path


def test_the_servers_checkout_is_used_when_this_seat_can_see_it(seat):
    """Terrence 2026-10-12: the server's own device-testing is the first place to look — it is the
    one the server reads campaign logs from."""
    srv = _checkout(seat.tmp / "mnt" / "testbox_home" / "claude" / "device-testing")
    _checkout(seat.tmp / "home" / "claude" / "device-testing")        # a home checkout loses to it
    seat.state["reply"] = {"dt_root": str(srv)}
    assert ck_agent.session_dt_root() == str(srv)
    assert seat.fetched == ["http://srv:8000"]


def test_an_explicit_dt_root_wins_and_the_server_is_not_asked(seat, monkeypatch):
    monkeypatch.setenv("CK_DT_ROOT", "/explicit")
    assert ck_agent.session_dt_root() == "/explicit"
    monkeypatch.delenv("CK_DT_ROOT")
    monkeypatch.setattr(ck_agent, "_CONF", {"origin": "http://srv:8000", "dt_root": "/conf"})
    assert ck_agent.session_dt_root() == "/conf"
    assert seat.fetched == []


def test_a_server_path_this_seat_cannot_see_falls_back_and_says_so(seat, monkeypatch):
    home = _checkout(seat.tmp / "home" / "claude" / "device-testing")
    seat.state["reply"] = {"dt_root": "/media/someone/mnt/testbox_home/claude/device-testing"}
    assert ck_agent.session_dt_root() == str(home)
    home_profile = home / ".claude" / "ask-ck-campaign.settings.json"
    home_profile.unlink()
    monkeypatch.setattr(ck_agent, "_sdk_loader", lambda: types.SimpleNamespace(__version__="0.0.test"))
    cap = ck_agent.session_capability()
    assert cap["available"] is False
    assert "/media/someone/mnt/testbox_home/claude/device-testing) is not visible from this seat" in cap["reason"]


def test_a_failed_lookup_is_retried_after_30_s_and_a_good_one_after_5_min(seat, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(ck_agent.time, "monotonic", lambda: clock[0])
    seat.state["reply"] = OSError("server down")
    ck_agent.session_dt_root(); ck_agent.session_dt_root()
    assert len(seat.fetched) == 1                       # cached, not hammered
    clock[0] += 31
    seat.state["reply"] = {"dt_root": "/somewhere"}
    ck_agent.session_dt_root()
    assert len(seat.fetched) == 2
    clock[0] += 299
    ck_agent.session_dt_root()
    assert len(seat.fetched) == 2
    clock[0] += 2
    ck_agent.session_dt_root()
    assert len(seat.fetched) == 3


def test_no_server_origin_means_no_lookup(seat, monkeypatch):
    monkeypatch.setattr(ck_agent, "_CONF", {"origin": "*"})
    assert ck_agent.session_dt_root().endswith("claude/device-testing")
    assert seat.fetched == []


# ---------------------------------------------------------------- parsing

# ---------------------------------------------------------------- closing: the final cost

def test_the_session_closes_on_the_result_after_askck_done_so_the_final_cost_is_kept(dt, monkeypatch):
    """1.3.3 and older closed on the marker and dropped the turn's result, so every run's recorded cost
    missed its last turn (run 0954-val-01c5: $1.49 without the tester's whole triage)."""
    use(monkeypatch, _campaign)
    s = ck_agent.get_session(ck_agent.start_session({"run_id": "r1", "handoff": HANDOFF})["session_id"])
    wait_state(s, ("done", "error", "stopped"))
    assert s.state == "done"
    kinds = [e["kind"] for e in s.events]
    done = next(i for i, e in enumerate(s.events) if e.get("marker") == "ASKCK-DONE")
    last = max(i for i, k in enumerate(kinds) if k == "result")
    assert last > done and s.events[last]["total_cost_usd"] == 2.75


def test_a_session_whose_final_result_never_comes_still_closes(dt, monkeypatch):
    async def script(client):
        yield AssistantMessage([TextBlock("ASKCK-DONE r1")])
        await asyncio.sleep(30)                          # no ResultMessage
        yield ResultMessage("too late")
    use(monkeypatch, script)
    monkeypatch.setattr(ck_agent, "DONE_RESULT_GRACE", 0.5)
    s = ck_agent.get_session(ck_agent.start_session({"run_id": "r1", "handoff": HANDOFF})["session_id"])
    wait_state(s, ("done", "error", "stopped"), timeout=5)
    assert s.state == "done" and "result" not in [e["kind"] for e in s.events]


def test_the_reasoning_text_reaches_the_page_and_is_never_read_for_markers(dt, monkeypatch):
    """1.3.4 dropped the text: run 2026-10-13T1454-val-43dd answered "how long will this take?" only
    in its reasoning ("This should take 30–45 minutes"), so the window showed nothing. The tester's
    reasoning travels too (its parent set); the window's Verbose option decides what is shown."""
    async def script(client):
        yield AssistantMessage([ThinkingBlock("This should take 30-45 minutes.\nRESULT AWPTCM-T1 PASS -- x -- y"),
                                TextBlock("Arming the sentinel.")])
        yield AssistantMessage([ThinkingBlock("x" * 5000)], parent="toolu_tester")
        yield AssistantMessage([ThinkingBlock("")])
        yield AssistantMessage([TextBlock("ASKCK-DONE r1")])
        yield ResultMessage("done")
    use(monkeypatch, script)
    s = ck_agent.get_session(ck_agent.start_session({"run_id": "r1", "handoff": HANDOFF})["session_id"])
    wait_state(s, ("done", "error", "stopped"))
    th = [e for e in s.events if e["kind"] == "thinking"]
    assert th[0]["text"].startswith("This should take 30-45 minutes.") and th[0]["parent"] is None
    assert th[1]["parent"] == "toolu_tester" and th[1]["text"].startswith("x" * ck_agent.THINKING_SHOW_MAX)
    assert len(th[1]["text"]) < 5000 and th[1]["text"].endswith(f"(+{5000 - ck_agent.THINKING_SHOW_MAX})")
    assert th[2]["text"] == ""
    assert [e["marker"] for e in s.events if e["kind"] == "marker"] == ["ASKCK-DONE"]


# ---------------------------------------------------------------- the sentinel's updates

def test_sentinel_updates_reach_the_page_without_waking_the_session(dt, monkeypatch):
    """device-testing's sentinel writes its Haiku updates to CK_SENTINEL_UPDATES instead of printing
    them into the session (run val-fbe9: 331 wake-ups, $35); the agent relays them as events."""
    async def script(client):
        path = client.options.env["CK_SENTINEL_UPDATES"]
        yield SystemMessage("init", {"session_id": "S", "model": "opus", "permissionMode": "auto", "cwd": "x"})
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": "06:57:31", "text": "TestCase_12 started on the fibre link.",
                                 "attention": None, "cost_usd": 0.0015}) + "\n")
            fh.write("not json\n")
            fh.write(json.dumps({"t": "06:58:01", "text": "", "attention": None, "cost_usd": 0.001}) + "\n")
            fh.write(json.dumps({"t": "06:58:13", "text": "stk_a power-cycled.", "attention":
                                 "[fw:test.log] !!FAIL: stk_a (member-3) contains 5 exceptions", "cost_usd": 0.002}) + "\n")
            fh.write('{"t": "06:58:40", "text": "half a li')          # still being written
        yield AssistantMessage([TextBlock("ASKCK-DONE r1")])
        yield ResultMessage("done")
    use(monkeypatch, script)
    s = ck_agent.get_session(ck_agent.start_session({"run_id": "r1", "handoff": HANDOFF})["session_id"])
    wait_state(s, ("done", "error", "stopped"))
    ups = [e for e in s.events if e["kind"] == "update"]
    assert [(u["text"], u["attention"], u["at"]) for u in ups] == [
        ("TestCase_12 started on the fibre link.", None, "06:57:31"),
        ("stk_a power-cycled.", "[fw:test.log] !!FAIL: stk_a (member-3) contains 5 exceptions", "06:58:13")]
    assert [u["cost_usd"] for u in ups] == [0.0015, 0.002]
    with open(s.updates_path, "a", encoding="utf-8") as fh:      # the partial line, finished
        fh.write('ne", "attention": null, "cost_usd": 0.001}\n')
    assert s.pump_updates() == 1 and s.events[-1]["text"] == "half a line"
    assert s.pump_updates() == 0


def test_marker_lines_take_only_line_starts():
    text = "intro\n  RESULT T1 PASS -- ok -- w.log\nsays RESULT inside\n`NOTIFY campaign -- x -- y`\nASKCK-DONE r9"
    assert [m["line"] for m in ck_agent.marker_lines(text)] == [
        "RESULT T1 PASS -- ok -- w.log", "NOTIFY campaign -- x -- y", "ASKCK-DONE r9"]


def test_marker_lines_take_the_validation_markers():
    # Verbatim from run 2026-10-13T0626-val-fbe9: Finalize waits on REVIEWED, and the 1.3.1 agent
    # dropped it, so the page said "the review has not been written" after a clean PASS.
    text = ("REVIEWED AWPTCM-T33235 tb470/IE520/port-2026-10-13T0626/33235/review.md\n\n"
            "Now §8: `/create-logs --auto` (T33235 is a script case, so it should be skipped).")
    assert [(m["marker"], m["line"]) for m in ck_agent.marker_lines(text)] == [
        ("REVIEWED", "REVIEWED AWPTCM-T33235 tb470/IE520/port-2026-10-13T0626/33235/review.md")]
    more = "REPAIRED AWPTCM-T1 tb470/x/work/t.py\nPROBE MATCH tb470.static\nthe REPAIRED copy is final"
    assert [m["marker"] for m in ck_agent.marker_lines(more)] == ["REPAIRED", "PROBE"]


def test_the_powershell_agent_says_sessions_are_not_available_on_windows():
    ps = (_REPO / "ask-ck" / "agent" / "ck-agent.ps1").read_text(encoding="utf-8")
    assert "sessions = [ordered]@{ available = $false" in ps


def test_the_seat_setup_installs_the_pinned_sdk_in_a_private_venv_and_runs_the_agent_with_it():
    sh = (_REPO / "ask-ck" / "agent" / "setup.sh").read_text(encoding="utf-8")
    assert 'SDK_PIN="0.2.165"' in sh and '"claude-agent-sdk==${SDK_PIN}"' in sh
    assert 'python3 -m venv "${AGENT_DIR}/venv"' in sh
    assert "ExecStart=${AGENT_PY} ${AGENT_DIR}/ck_agent.py" in sh and 'exec setsid nohup "$AGENT_PY" ck_agent.py' in sh
    assert 'echo "dt_root=${CK_DT_ROOT}"' in sh     # only an explicit one (2026-10-12)
    import subprocess
    assert subprocess.run(["bash", "-n", str(_REPO / "ask-ck" / "agent" / "setup.sh")]).returncode == 0


# ---------------------------------------------------------------- after-hours runs (D3, P4)

def test_the_poller_claims_a_due_run_starts_it_and_relays_every_event_to_the_server(dt, monkeypatch):
    from http.server import BaseHTTPRequestHandler
    got = {"claims": 0, "events": []}
    handoff = dict(HANDOFF)

    class S(BaseHTTPRequestHandler):
        def _send(self, obj, code=200):
            b = json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
        def do_GET(self):
            self._send({"due": [{"run_id": "r1"}] if got["claims"] == 0 else []})
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or b"{}")
            if self.path.endswith("/claim"):
                got["claims"] += 1
                return self._send({"handoff": handoff}) if got["claims"] == 1 else self._send({"detail": "claimed"}, 409)
            got["events"] += body["events"]; self._send({"ok": True})
        def log_message(self, *a): pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), S)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    use(monkeypatch, _campaign)
    assert ck_agent.poll_schedule_once(base) == ["r1"]
    assert ck_agent.poll_schedule_once(base) == []                       # never twice
    s = next(iter(ck_agent._SESSIONS.values()))
    wait_state(s, ("done",))
    t0 = time.time()
    while len(got["events"]) < len(s.events) and time.time() - t0 < 10:
        time.sleep(0.05)
    assert [e["seq"] for e in got["events"]] == list(range(len(s.events)))
    srv.shutdown()
