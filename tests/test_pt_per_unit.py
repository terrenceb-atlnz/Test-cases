"""Per-unit generation: one LLM call per TestCase, spliced into a frame we render.

WHAT THIS IS (PLAN-pytest-creator.md §9.5, built 2026-09-02)
-----------------------------------------------------------
§9.5 proposed a "Pass A" that asked an LLM to write the imports, the TestSet class and the
`ts.add_testCase(...)` runner. `_render_skeleton()` already produces all of that
deterministically, so Pass A was asking a model to reproduce something we can generate
exactly — and to reproduce it consistently across N separate calls. It is gone. The frame
is rendered, the units are generated, the server splices.

Four properties are load-bearing.

1. UNIT IDS ARE NOT SEQUENCE STEP NUMBERS. `_split_sequence` renumbers: setup-kind steps
   become TestSet.configure() and the remainder are renumbered contiguously, so sequence
   step 31 can be TestCase_29. Keying chunks on the sequence number would mis-file every
   unit on any case that has a setup step — AWPTCM-T44297 has two.

2. SPLICING MUST BE EXACT. Substituting each unit's own block back into the frame has to
   reproduce the frame byte-for-byte, or the units do not fit the file they were cut from.
   Verified against the real 781-line T44297 frame in the round-trip test below.

3. A WRONG UNIT IS REFUSED ON ARRIVAL, not at assembly. Same reasoning as
   `_recovery_failure`: the reviewer should learn a call was wrong while looking at the
   button they pressed, not thirty units later when the file will not compile.

4. ASSEMBLY USES NO LLM. It is a local splice, a re-stamp and a lint. If an LLM ever
   appears in it, the wall-clock and provenance arguments for this whole design are void.

NOT PINNED: the prompt's wording, the exact worker/retry numbers, or how a real model
formats a unit.
"""
import os
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from routers import pytest_create as pc  # noqa: E402

_SRC = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
# Structural assertions read CODE, never the prose about it.
_CODE = re.sub(r'#[^\n]*', '', re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', '', _SRC))


def _slice(start: str, end: str) -> str:
    return _CODE[_CODE.index(start):_CODE.index(end)]


# The one implementation of "call the model, shape-check the reply, record the chunk".
CALL = _slice("def _unit_call_and_store", '@router.post("/generate_units/')
BATCH = _slice('@router.post("/generate_units/', '@router.get("/units_status/')
STEP = _slice('@router.post("/generate_step/', "def _review_lint_findings")

FRAME = '''#!/usr/bin/python3
import sys
from framework import ATTestSet, ATTestCase


class TestSet(ATTestSet.TestSet):

    def init(self, setup):
        self.dut = setup.init_swi('swi_a')

    def configure(self):
        # >>> FILL: the configuration commands <<<
        pass

    def tear_down(self):
        # >>> FILL: commands undoing configure() <<<
        pass


class TestCase_1(ATTestCase.TestCase):
    testCaseDesc = "one"
    testCaseRef = 'AWPTCM-T1'

    def main(self):
        self.log("STEP 1: one")
        # >>> FILL <<<
        pass


class TestCase_2(ATTestCase.TestCase):
    testCaseDesc = "two"
    testCaseRef = 'AWPTCM-T1'

    def main(self):
        """A docstring that mentions class TestCase_99 to bait a regex."""
        self.log("STEP 2: two")
        pass


if __name__ == '__main__':
    ts = TestSet()
    ts.add_testCase(TestCase_1())
    ts.add_testCase(TestCase_2())
    ts.run(sys.argv)
'''


def _units():
    return pc._skeleton_units(FRAME)


# --- unit discovery ---------------------------------------------------------------

def test_it_finds_the_setup_pair_and_every_testcase():
    us = _units()
    assert [u["id"] for u in us] == ["setup", "tc1", "tc2"]
    assert [u["kind"] for u in us] == ["setup", "testcase", "testcase"]


def test_configure_and_tear_down_are_ONE_unit():
    """They are a matched pair — what configure sets up, tear_down reverts. Split across
    two calls the halves can disagree about what was configured."""
    setup = _units()[0]
    assert "def configure" in setup["block"]
    assert "def tear_down" in setup["block"]


def test_a_class_name_inside_a_docstring_is_not_a_unit():
    # Read off the AST, not by regex. TestCase_99 appears in tc2's docstring.
    assert "tc99" not in [u["id"] for u in _units()]


def test_units_come_back_in_file_order():
    us = _units()
    assert [u["lines"][0] for u in us] == sorted(u["lines"][0] for u in us)


def test_an_unparseable_frame_yields_no_units_rather_than_raising():
    assert pc._skeleton_units("class Broken(:\n") == []


def test_unit_ids_are_not_sequence_numbers():
    """The renumbering trap. tc_n counts TestCase classes; the sequence row it implements
    is resolved separately by _unit_source_step."""
    fn = _CODE[_CODE.index("def _unit_source_step"):_CODE.index("def _pt_generation_context")]
    assert "tc_n" in fn and "tc_steps" in fn


def test_a_testcase_unit_maps_to_its_renumbered_sequence_row():
    tc_steps = [{"n": 1, "action": "a"}, {"n": 2, "action": "b"}]
    us = _units()
    assert pc._unit_source_step(us[1], tc_steps)["action"] == "a"
    assert pc._unit_source_step(us[2], tc_steps)["action"] == "b"
    assert pc._unit_source_step(us[0], tc_steps) is None       # setup has no row


# --- assembly ---------------------------------------------------------------------

def test_splicing_each_unit_back_reproduces_the_frame_exactly():
    us = _units()
    ctx = {"skeleton": FRAME, "units": us}
    chunks = {u["id"]: {"status": "ok", "code": u["block"]} for u in us}
    out, missing = pc._assemble_units(ctx, chunks)
    assert missing == []
    assert out == FRAME, "a unit that does not splice back cleanly does not fit the file"


def test_replacing_units_of_different_length_does_not_shift_the_others():
    """Back-to-front is why this works. Front-to-back, replacing a 20-line unit with a
    60-line one moves every later unit's recorded line range and the next splice lands in
    the wrong place."""
    us = _units()
    ctx = {"skeleton": FRAME, "units": us}
    chunks = {
        "setup": {"status": "ok", "code": "    def configure(self):\n        pass\n\n"
                                          "    def tear_down(self):\n        pass"},
        "tc1": {"status": "ok", "code": "class TestCase_1(ATTestCase.TestCase):\n"
                                       + "\n".join("    # pad %d" % i for i in range(40))
                                       + "\n    def main(self):\n        pass"},
        "tc2": {"status": "ok", "code": "class TestCase_2(ATTestCase.TestCase):\n"
                                       "    def main(self):\n        pass"},
    }
    out, missing = pc._assemble_units(ctx, chunks)
    assert missing == []
    import ast
    tree = ast.parse(out)                       # still valid Python
    names = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    assert names == ["TestSet", "TestCase_1", "TestCase_2"]
    assert out.count("def main") == 2
    assert "# pad 39" in out


def test_an_ungenerated_unit_is_reported_not_silently_left_blank():
    us = _units()
    ctx = {"skeleton": FRAME, "units": us}
    out, missing = pc._assemble_units(ctx, {"tc1": {"status": "ok", "code": us[1]["block"]}})
    assert missing == ["setup", "tc2"]


def test_a_failed_unit_counts_as_missing():
    us = _units()
    ctx = {"skeleton": FRAME, "units": us}
    chunks = {u["id"]: {"status": "ok", "code": u["block"]} for u in us}
    chunks["tc2"] = {"status": "error", "error": "boom", "code": ""}
    _out, missing = pc._assemble_units(ctx, chunks)
    assert missing == ["tc2"]


def test_assembly_never_calls_an_llm():
    body = _CODE[_CODE.index("async def assemble_script"):]
    body = body[:body.index("@router")] if "@router" in body[10:] else body
    for forbidden in ("run_prompt", "run_prompt_text", "_call_llm"):
        assert forbidden not in body, f"assembly must be local — found {forbidden}"


def test_assembly_refuses_an_incomplete_set():
    body = _CODE[_CODE.index("async def assemble_script"):]
    assert "409" in body[:2500]


def test_assembly_drops_a_review_of_the_previous_artefact():
    # Findings were about a different script; leaving them attributes them to this one.
    body = _CODE[_CODE.index("async def assemble_script"):]
    assert 'pop("review", None)' in body[:3000]


# --- shape checking on arrival ----------------------------------------------------

def _tc():
    return _units()[1]


def test_a_units_own_block_passes():
    ok, why = pc._unit_shape_ok(_tc()["block"], _tc())
    assert ok, why


def test_a_reply_naming_a_different_class_is_refused():
    u = _tc()
    ok, why = pc._unit_shape_ok(u["block"].replace("TestCase_1", "TestCase_7"), u)
    assert not ok and "TestCase_7" in why


def test_a_reply_with_two_classes_is_refused():
    u = _tc()
    ok, why = pc._unit_shape_ok(u["block"] + "\n\n\nclass Extra:\n    pass\n", u)
    assert not ok and "one class" in why


def test_a_reply_without_main_is_refused():
    u = _tc()
    code = "class TestCase_1(ATTestCase.TestCase):\n    testCaseDesc = 'x'\n"
    ok, why = pc._unit_shape_ok(code, u)
    assert not ok and "main()" in why


def test_a_reply_that_does_not_parse_is_refused():
    ok, why = pc._unit_shape_ok("class TestCase_1(:\n    pass", _tc())
    assert not ok and "valid Python" in why


def test_the_setup_unit_must_return_both_methods():
    setup = _units()[0]
    ok, why = pc._unit_shape_ok(setup["block"], setup)
    assert ok, why
    half = "    def configure(self):\n        pass"
    ok, why = pc._unit_shape_ok(half, setup)
    assert not ok and "tear_down" in why


# --- prompt scoping ---------------------------------------------------------------

def test_the_per_unit_prompt_shares_ONE_copy_of_the_fill_rules():
    """Extracted to pt_fill_rules.jinja so the whole-script and per-unit prompts cannot
    drift. test_pt_prompt_rules_partial asserts the extraction changed nothing."""
    D = _SERVER / "templates" / "prompts"
    step = (D / "pt_generate_step.jinja").read_text(encoding="utf-8")
    whole = (D / "pt_generate_script.jinja").read_text(encoding="utf-8")
    assert (D / "pt_fill_rules.jinja").exists()
    assert "{% include 'pt_fill_rules.jinja' %}" in step
    assert "{% include 'pt_fill_rules.jinja' %}" in whole


def test_the_per_unit_prompt_asks_for_one_block_and_forbids_the_frame():
    step = (_SERVER / "templates" / "prompts" / "pt_generate_step.jinja").read_text(encoding="utf-8")
    assert "ONE fenced python block" in step
    assert re.search(r"do\s+not write imports", step)
    assert "__main__" in step


def test_the_per_unit_prompt_carries_the_verify_contract():
    step = (_SERVER / "templates" / "prompts" / "pt_generate_step.jinja").read_text(encoding="utf-8")
    assert "step.verify" in step
    assert "contract" in step


def test_only_this_units_fragments_go_into_its_prompt():
    """The input saving. The whole-script prompt carried 106KB of fragment code because it
    carried every fragment for every step."""
    ctx = {"fragments": [{"source_id": "a.py", "symbol": "x", "maps_to": [1], "code": "c"},
                         {"source_id": "b.py", "symbol": "y", "maps_to": [2], "code": "c"}],
           "setup_steps": [], "tc_steps": [{"n": 1, "action": "a"}, {"n": 2, "action": "b"}]}
    got = pc._fragments_for_unit(_units()[1], ctx)
    assert [f["symbol"] for f in got] == ["x"]


def test_the_setup_unit_gets_the_setup_steps_fragments():
    ctx = {"fragments": [{"source_id": "a.py", "symbol": "s", "maps_to": [9], "code": "c"}],
           "setup_steps": [{"n": 9, "action": "configure"}], "tc_steps": []}
    got = pc._fragments_for_unit(_units()[0], ctx)
    assert [f["symbol"] for f in got] == ["s"]


# --- the edited prompt is sent verbatim -------------------------------------------

def test_an_edited_prompt_is_sent_as_written_not_re_rendered():
    """The editable frame is pointless if dispatch re-renders from the template."""
    assert "run_prompt_text" in CALL
    assert "run_prompt(" not in CALL
    # Both entry points read the reviewer's prompt off the request.
    assert 'body.get("prompt")' in STEP
    assert 'w.get("prompt")' in BATCH


def test_run_prompt_text_goes_through_the_same_instrumented_choke_point():
    # Not a side door around timing/usage/debug-logging — only around Jinja.
    llm = (_SERVER / "llm.py").read_text(encoding="utf-8")
    fn = llm[llm.index("def run_prompt_text"):llm.index("def _health_ping")]
    assert "_call_llm_with_meta" in fn
    assert "_resolve_llm_runtime" in fn


def test_prompts_are_rendered_not_stored_unless_edited():
    """§9.7: 'a 6-chunk generation must not store six 85KB prompts'."""
    body = _CODE[_CODE.index("async def step_prompts"):_CODE.index("async def generate_step")]
    assert "_render_unit_prompt" in body
    assert 'if edited else {}' in CALL, "an unedited prompt must not be persisted"


# --- concurrent writes ------------------------------------------------------------

def test_chunk_writes_get_a_retry_budget_above_the_worker_bound():
    """N units land at once and every reply writes the same session row, so a stale write
    is the norm here. The default budget of 3 was sized for 'a human clicked Save
    mid-call'; a discarded chunk costs a whole LLM call."""
    assert pc._PT_CHUNK_WRITE_ATTEMPTS > 16   # the broker's own max worker count
    # Every persist on the unit path, not just one: success and failure are equally
    # subject to the same contention, and a discarded failure record loses the reason a
    # pill is red. The batch's crash handler counts too.
    for region, name in ((CALL, "_unit_call_and_store"), (BATCH, "generate_units")):
        n = region.count("_pt_persist_fresh(")
        assert region.count("attempts=_PT_CHUNK_WRITE_ATTEMPTS") == n, name


def test_the_retry_backoff_is_jittered():
    """Without jitter, N units that collided once re-collide in lockstep every retry."""
    fn = _CODE[_CODE.index("def _pt_persist_fresh"):_CODE.index("def _llm_cfg")]
    assert "random" in fn and "sleep" in fn


def test_a_failed_unit_records_its_error_before_raising():
    """Record, then refuse — the 2026-08-04 lesson. A pill has to be able to say WHY."""
    # Every refusal records before it returns. Three of them — LLM error, no fenced
    # block, wrong shape — and each goes through the one _fail() that persists.
    assert '"status": "error"' in CALL
    assert "_pt_persist_fresh" in CALL
    calls = len(re.findall(r"(?<![_A-Za-z])_fail\(", CALL))
    assert calls == 4, "3 refusal paths + the definition itself"
    # A crashed batch task must not leave a pill yellow forever with no reason.
    assert '"status": "error"' in BATCH
    assert "dispatch failed" in BATCH


# --- the fan-out must not hold a connection per unit ------------------------------
#
# THE DEADLOCK (2026-09-02, AWPTCM-T44297 — found on the live server, not by a test)
# ---------------------------------------------------------------------------------
# The first per-unit UI fired one `/generate_step` per unit and awaited each. Every one
# holds its connection for the whole LLM call, because the request blocks in
# `registry.submit` until the browser posts a result. A browser allows SIX connections
# per origin. So 30 requests fired, 6 took every connection and blocked, and the broker's
# own `/api/agent/next` long-poll could no longer get one. Nothing was claimed, nothing
# returned, no connection was freed. Measured live: `pending: 5` (only ~6 of 30 requests
# reached the server at all), `session_active: false`, zero `claude` processes, zero LLM
# records. Raising ckBrokerWorkers made it WORSE — each worker holds a long-poll too.
#
# No test could have caught it: jsdom's stubbed fetch has no connection limit, so the
# fan-out spec passed either way. It proved the code DISPATCHES concurrently, not that
# the transport could carry it. What IS checkable is the property that replaced it —
# the fan-out endpoint must return without waiting for the work.

def test_the_batch_dispatch_does_not_wait_for_the_work():
    """The whole point. If generate_units awaits its tasks it is the deadlock again with
    one connection instead of thirty."""
    assert "asyncio.create_task" in BATCH
    assert not re.search(r"await\s+asyncio\.gather", BATCH)
    assert not re.search(r"await\s+_one\(", BATCH)


def test_the_batch_returns_what_it_dispatched():
    assert '"dispatched"' in BATCH


def test_a_second_dispatch_cannot_double_run_a_unit():
    """Two clicks, or a re-run of a unit already in flight, would spend the seat twice and
    race two writers onto the same chunk."""
    assert "_pt_units_inflight" in BATCH
    assert "already_running" in BATCH
    # The guard is the FILTER, not the mention: a version that computes `already` and then
    # dispatches everything anyway reports honestly and still double-runs.
    assert re.search(r"if uid not in already", BATCH)


def test_the_in_flight_mark_is_cleared_even_when_a_task_crashes():
    # Otherwise the pill stays yellow for the life of the process.
    assert re.search(r"finally:\s*\n\s*_pt_unit_mark\(key, \[uid\], False\)", BATCH)


def test_server_side_concurrency_is_capped():
    """30 blocking calls would take 30 of anyio's 40 default threadpool threads. The real
    ceiling on throughput is the browser's broker worker count, which is smaller — so this
    protects the server rather than pacing the work."""
    assert "Semaphore(_PT_UNIT_DISPATCH_MAX)" in BATCH
    # Created AND acquired. A semaphore nobody waits on caps nothing.
    assert re.search(r"async with sem:", BATCH)
    assert pc._PT_UNIT_DISPATCH_MAX <= 16


def test_the_status_poll_does_not_ship_the_code_back_every_time():
    """30 units of ~2.5KB on a 2s poll is 150KB/minute of unchanged bytes. The UI fetches
    a unit's code when its page is opened."""
    status = _slice('@router.get("/units_status/', '@router.post("/generate_step/')
    assert '"chars"' in status
    # It READS the code to measure it; the property is that it never RETURNS it, so look
    # for the output-dict key rather than any mention of the word.
    assert '"code":' not in status


def test_the_status_poll_reports_running_units_that_have_no_chunk_yet():
    # A dispatched unit has nothing in step6.chunks until it lands; without this the pill
    # would drop back to red the moment it was dispatched.
    status = _slice('@router.get("/units_status/', '@router.post("/generate_step/')
    assert "setdefault" in status and '"running"' in status


def test_both_entry_points_share_one_call_implementation():
    """A second copy of call/shape-check/record would drift, and the shape check is what
    stands between a wrong reply and a file that will not compile."""
    assert "_unit_call_and_store" in BATCH
    assert "_unit_call_and_store" in STEP
    assert STEP.count("_parse_generated_blocks") == 0
    assert CALL.count("_parse_generated_blocks") == 1


# --- prompt-prefix caching (reordered 2026-09-02) -----------------------------------
# Prompt caching can only reuse a literal shared PREFIX. Before the reorder the fill rules
# sat LAST in pt_generate_step.jinja, so the 30 unit prompts of AWPTCM-T44297 shared 343
# characters — 0.7% of an average prompt. Hoisting every invariant block above the first
# varying one took the measured shared prefix to 11,143 characters (21.7%). These pin the
# ORDER that buys that; they deliberately do not pin the measured number, which moves with
# the case.

_STEP_TPL = (_SERVER / "templates" / "prompts" / "pt_generate_step.jinja").read_text(encoding="utf-8")
# Order assertions must read the template BODY, not the header comment that explains it —
# the header names every block in both groups, so a naive index() finds the wrong one.
_STEP_BODY = _STEP_TPL[_STEP_TPL.index("-#}") + 3:]


def test_every_invariant_prompt_block_precedes_every_varying_one():
    """The whole point of the ordering.

    `cli_reference` is in the VARYING group: `_cli_reference_block(text_rows, frags)`
    derives it from this unit's own step text and fragments, and T44297's 30 blocks all
    differ. It can only sit there because pt_fill_rules.jinja was reworded to drop the word
    "above" (2026-09-02) — see test_pt_prompt_rules_partial. Putting it back above the
    rules was measured at half the shared prefix: 11,143 -> 5,663 chars.
    """
    invariant = ["case_key", "framework_surface", "devices",
                 "{% include 'pt_fill_rules.jinja' %}"]
    varying = ["mode ==", "blank_block", "fragments", "cli_reference"]
    last_invariant = max(_STEP_BODY.index(t) for t in invariant)
    first_varying = min(_STEP_BODY.index(t) for t in varying)
    assert last_invariant < first_varying, (
        "an invariant block sank below a varying one — the shared prefix is truncated at "
        "whichever varying block now comes first")


def test_the_fill_rules_are_inside_the_shared_prefix():
    """The rules are the single biggest invariant block (14,794 chars, 29% of a 30-unit
    fan-out's entire input spend). If they follow any per-unit content they cannot be
    cached, which is exactly the state this reorder fixed."""
    assert (_STEP_BODY.index("{% include 'pt_fill_rules.jinja' %}")
            < _STEP_BODY.index("## Your unit"))


def test_two_units_of_one_case_share_a_prefix_reaching_into_the_fill_rules():
    """Render-level proof rather than a source-order proxy.

    MEASURED on AWPTCM-T44297, 2026-09-02: 11,143 chars — 21.7% of an average unit prompt,
    up from 343 (0.7%) before the reorder.

    This fixture holds `device_note` equal between the two units, so it proves the ordering
    in isolation: the ENTIRE invariant region is shared. Production reaches 11,143 of those
    20,335 chars rather than all of them, because two values are interpolated INSIDE
    pt_fill_rules.jinja and genuinely vary:

      * `device_note`   (rules line 72) — built from THIS unit's fragments. Caps at 11,143.
      * `cli_reference` (rules line 86) — rule 4b branches on whether one exists, capping a
        case at 6,489. It does not bite on T44297, where all 30 units have one.

    Both are open decisions deferred by Terrence on 2026-09-02 pending real cost figures,
    not defects to quietly fix here.
    """
    from llm import render_prompt

    base = {
        "case_key": "AWPTCM-T00001", "case_title": "A case",
        "setup_steps": [{"n": 1, "action": "configure"}],
        "devices": ["dut", "tb"],
        "framework_surface": {"framework.ATLibrary": {"classes": {}, "functions": []}},
        "device_note": "Reused fragments reference these device names: dut.",
        "py2_flagged": False, "model_name": "m", "gen_date": "2026-09-02",
    }
    a = render_prompt("pt_generate_step.jinja", {
        **base, "mode": "case", "tc_n": 1, "source_n": 1,
        "step": {"action": "act one", "verify": "ver one"},
        "blank_block": "class TestCase_1:\n    pass\n",
        "fragments": [{"source_id": "a.py", "symbol": "x", "code": "c", "why": "w",
                       "tag": "t", "py2_flagged": False}],
        "cli_reference": "REAL CLI REFERENCE\nshow lldp neighbors",
    })
    b = render_prompt("pt_generate_step.jinja", {
        **base, "mode": "case", "tc_n": 24, "source_n": 26,
        "step": {"action": "act two", "verify": "ver two"},
        "blank_block": "class TestCase_24:\n    pass\n",
        "fragments": [],
        "cli_reference": "REAL CLI REFERENCE\nclear exception log",
    })
    n = len(os.path.commonprefix([a, b]))
    rules_start = a.index("The rules below are the project's rules")
    assert n > rules_start, (
        f"shared prefix is {n} chars, short of the fill rules at {rules_start} — a varying "
        "block was hoisted above the line and the reorder is undone")
    assert "{{" not in a and "%}" not in a          # rendered, not a template dump
    assert "DEVICE NAME RECONCILIATION" in a[:n]    # the rules really are inside the prefix
    # `device_note` is held equal in this fixture, so here the prefix reaches the FULL
    # invariant region. Production does not: T44297 measures 11,143 of these 20,335 chars
    # because that one value is built per unit. See the docstring.
    assert n >= a.index("## Your unit")


def test_the_shared_rules_carry_no_positional_pointer_to_the_cli_reference():
    """The rules are included by BOTH prompts, which put the CLI reference on opposite
    sides of them. A word like "above" is therefore false for one caller, and reintroducing
    one would force the reference back above the rules — halving the shared prefix."""
    rules = (_SERVER / "templates" / "prompts" / "pt_fill_rules.jinja").read_text(encoding="utf-8")
    for bad in ("CLI REFERENCE above", "injected above", "reference above"):
        assert bad not in rules, f"positional pointer {bad!r} is back in the shared rules"
