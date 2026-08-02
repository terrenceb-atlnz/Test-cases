"""Every LLM step must name its own timeout — inheriting the 180s default is a bug.

THE DEFECT THIS PINS (found 2026-07-30, autopilot batch)
--------------------------------------------------------
`run_prompt(...)` defaults to `timeout=180`. Every LLM call in the PyTest Creator router
passed an explicit, larger timeout — `suggest_scripts` 300, `gather_fragments` 300,
`generate_script` 600, `fix_script` 600 — except `extract_sequence`, which passed none and
so silently ran on 180s. Sequence extraction emits one row (action + verify + kind) per
Zephyr step, so its output grows with the refined case; on a 42-step case it timed out at
exactly 180s on every attempt, including the retry.

What makes it worth a structural test rather than a one-line fix: the failure is
*misattributed*. The 502 body is the CLI's own message —
"LLM call failed (claude via claude_code): CLI call timed out after 180s" — so it reads as
a model/transport fault, and the natural response is to blame the LLM or raise the client
timeout, neither of which touches the missing kwarg. The same shape can return the moment
someone adds a new step and forgets the argument, and it will fail only on large cases:
green in tests, green on small demos, dead on real work.

The check is deliberately about the ARGUMENT BEING PRESENT, not its value. Pinning numbers
would turn every tuning change into a test edit, which trains people to update the
assertion instead of thinking. What must never happen again is a call with no opinion at
all.
"""
import ast
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
_PT_ROUTER = _SERVER / "routers" / "pytest_create.py"
_LLM = _SERVER / "llm.py"

sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))
import llm  # noqa: E402  (CK_server flat-module layout)

# `run_prompt` is the generic templated-LLM entry point. Keep this list as the set of
# call targets whose timeout is meant to be a per-step decision.
_LLM_ENTRY_POINTS = {"run_prompt"}


def _run_prompt_calls(path: Path):
    """(lineno, template_name, {kwarg names}) for every run_prompt call in `path`.

    Handles both direct `run_prompt(...)` and the router's actual shape,
    `run_in_threadpool(run_prompt, "tmpl.jinja", {...}, timeout=..., ...)` — the kwargs
    ride on the OUTER call in that form, which is exactly why a plain grep for
    'run_prompt' followed by 'timeout' on the same line finds nothing useful.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = getattr(func, "id", None) or getattr(func, "attr", None)
        args = node.args
        if name in _LLM_ENTRY_POINTS:
            target_args = args
        elif name == "run_in_threadpool" and args and getattr(args[0], "id", None) in _LLM_ENTRY_POINTS:
            target_args = args[1:]
        else:
            continue
        template = None
        if target_args and isinstance(target_args[0], ast.Constant) and isinstance(target_args[0].value, str):
            template = target_args[0].value
        out.append((node.lineno, template, {kw.arg for kw in node.keywords}))
    return out


def test_the_scan_actually_finds_the_calls():
    """Guard the guard. A structural check that silently matches nothing passes forever
    while covering nothing — the failure mode tests/_wizard_src.py exists to prevent.
    """
    calls = _run_prompt_calls(_PT_ROUTER)
    assert len(calls) >= 5, f"expected to find the router's LLM calls, found {len(calls)}"
    templates = {t for _, t, _ in calls if t}
    assert "pt_extract_sequence.jinja" in templates, (
        f"the regressed call site is not being scanned; templates seen: {sorted(templates)}")


@pytest.mark.parametrize("lineno,template,kwargs", _run_prompt_calls(_PT_ROUTER),
                         ids=lambda v: str(v))
def test_every_llm_call_sets_its_own_timeout(lineno, template, kwargs):
    assert "timeout" in kwargs, (
        f"routers/pytest_create.py:{lineno} calls run_prompt for {template!r} without an "
        f"explicit timeout, so it inherits run_prompt's 180s default. Output for this step "
        f"scales with the case, and the resulting 502 blames the LLM, not the missing "
        f"kwarg. Choose a timeout: ~300s for an analysis step, ~600s for one that emits a "
        f"whole artefact.")


def test_sequence_extraction_is_in_the_large_output_tier():
    """The specific regression: sequence extraction emits one row per source step, so it
    belongs with generation (600s), not with the short analysis steps (300s). Asserted as
    a floor, not an equality, so raising it later needs no test edit."""
    calls = {t: (ln, kw) for ln, t, kw in _run_prompt_calls(_PT_ROUTER) if t}
    assert "pt_extract_sequence.jinja" in calls
    tree = ast.parse(_PT_ROUTER.read_text(encoding="utf-8"))
    found = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        args = node.args
        if getattr(node.func, "id", None) != "run_in_threadpool" or not args:
            continue
        if getattr(args[0], "id", None) != "run_prompt":
            continue
        if not (len(args) > 1 and isinstance(args[1], ast.Constant)
                and args[1].value == "pt_extract_sequence.jinja"):
            continue
        for kw in node.keywords:
            if kw.arg == "timeout" and isinstance(kw.value, ast.Constant):
                found = kw.value.value
    assert found is not None, "extract_sequence's timeout is not a plain literal any more"
    assert found >= 300, (
        f"extract_sequence timeout is {found}s. A 42-step refined case exceeded 180s; "
        f"anything in the analysis-step tier will start failing on rich cases again.")


# ---------------------------------------------------------------------------
# The whole-response floor for non-streaming CLI backends
# ---------------------------------------------------------------------------
# Raising extract_sequence to 600s fixed one call site and the NEXT step then failed at
# its own 300s. The shared cause: every timeout here was sized against the STREAMING vLLM
# path, where the number bounds the gap between chunks; a headless CLI subprocess gets one
# shot at the whole response, so the identical number is a whole-artefact budget. llm.py
# floors the CLI budget in one place instead of re-tuning five call sites per backend.


def test_the_floor_lifts_real_caller_budgets():
    """The five values the routers actually pass must all clear the floor."""
    for asked in (180, 300, 600):
        assert llm._cli_timeout(asked) == llm._CLI_WHOLE_RESPONSE_FLOOR


def test_the_floor_never_lowers_a_bigger_request():
    """A caller asking for more than the floor keeps it — max(), not assignment."""
    bigger = llm._CLI_WHOLE_RESPONSE_FLOOR + 600
    assert llm._cli_timeout(bigger) == bigger


def test_a_deliberately_short_timeout_stays_short():
    """Without this guard the health check becomes a half-hour hang instead of a health
    check — the one call whose whole value is failing fast."""
    assert llm._cli_timeout(30) == 30
    assert llm._cli_timeout(119) == 119


def test_the_health_ping_stays_under_the_guard():
    """Ties the guard's threshold to the caller it exists to protect.

    The `>= 120` cut-off is only meaningful while the health ping asks for less than that.
    If someone raises the ping's timeout past the threshold, the ping silently inherits a
    1800s budget and this test is the only thing that would say so.
    """
    src = _LLM.read_text(encoding="utf-8")
    body = src[src.index("def _health_ping("):]
    body = body[:body.index("\ndef ")]
    asked = [int(m) for m in __import__("re").findall(r"timeout=(\d+)", body)]
    assert asked, "could not find the health ping's timeout any more"
    for t in asked:
        assert llm._cli_timeout(t) == t, (
            f"the health ping asks for {t}s, which the CLI floor now lifts to "
            f"{llm._cli_timeout(t)}s — a failing health check would hang instead of "
            f"reporting. Keep the ping under the guard, or give it an explicit opt-out.")


@pytest.mark.parametrize("auth_method,floored", [
    ("claude_code", True),
    ("grok_cli", True),
    # claude_agent deliberately keeps the caller's number: the same timeout bounds the
    # agent-bridge long-poll a user's browser is holding open.
    ("claude_agent", False),
])
def test_the_floor_is_wired_into_the_right_dispatch_arms(auth_method, floored):
    """Structural: a floor helper nobody calls is decorative. Checks the dispatch line for
    each headless arm rather than trusting the helper's existence."""
    src = _LLM.read_text(encoding="utf-8")
    arm = src[src.index(f'auth_method == "{auth_method}"'):]
    arm = arm[:arm.index("\n    if ") if "\n    if " in arm else min(len(arm), 400)]
    assert ("_cli_timeout(timeout)" in arm) is floored, (
        f"the {auth_method} dispatch {'should' if floored else 'should NOT'} pass its "
        f"timeout through _cli_timeout(); arm reads:\n{arm[:300]}")
