"""Slice D (PLAN-generate-state-and-sequence-sanity, 2026-09-21): Review and Fix see the library.

WHY. The generated script does `from library_awptcm_<case> import *` and the module ships
beside it, but `review_script` and `fix_script` rendered their prompts from the script alone.
On AWPTCM-T33234 (2026-09-18) 4 of the final 5 review findings were false for exactly this
reason: `waitForLinkState(..., 'down')` (the helper handles 'down' explicitly),
`checkCurrentPort(..., 'auto', ...)` ('auto' = "a negotiated value is present") and
`expect_value=True` (declared in the def) were all reported as defects. A Fix that cannot see
the library "fixes" a correct call the same way.

Pinned here:
  * both endpoints hand the library (name + code) to their prompt context;
  * both templates render the module as an AUTHORITATIVE block, only when present;
  * both templates carry a rule that a call matching the library is correct, not a finding.
Offline: templates rendered with jinja2, the endpoint bodies read as code.
"""
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SERVER = _REPO / "ask-ck" / "CK-main" / "CK_server"
sys.path.insert(0, str(_REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(_SERVER))

from routers import pytest_create as pc  # noqa: E402

_PROMPTS = _SERVER / "templates" / "prompts"
_SRC = (_SERVER / "routers" / "pytest_create.py").read_text(encoding="utf-8")
_CODE = re.sub(r'#[^\n]*', '',
               re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', '', _SRC))

LIB = "def waitForLinkState(testCase, device, port, wanted, timeout=60):\n    '''down is handled'''\n"


def _render(name, **ctx):
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(_PROMPTS)))
    base = {"case_key": "AWPTCM-T1", "file_name": "t.py", "code": "print(1)", "sequence": [],
            "lint_findings": [], "iteration": 1, "lint_errors": "", "review_findings": [],
            "results": [], "log_excerpts": [], "library_name": "", "library_code": ""}
    base.update(ctx)
    return env.get_template(name).render(**base)


# --- the context helper --------------------------------------------------------------

def test_the_helper_reads_the_companion_library_off_step6():
    step6 = {"files": {"test": {"name": "t.py", "code": "x"},
                       "library": {"name": "library_awptcm_t1.py", "code": LIB}}}
    ctx = pc._library_prompt_context(step6)
    assert ctx == {"library_name": "library_awptcm_t1.py", "library_code": LIB}


def test_the_helper_is_empty_strings_when_the_suite_has_no_library():
    assert pc._library_prompt_context({"files": {"test": {"name": "t.py", "code": "x"}}}) == \
        {"library_name": "", "library_code": ""}
    assert pc._library_prompt_context({}) == {"library_name": "", "library_code": ""}


# --- both endpoints pass it ------------------------------------------------------------

def _body(start, end):
    i = _CODE.index(start)
    j = _CODE.index(end, i)
    return _CODE[i:j]


def test_review_script_hands_the_library_to_its_prompt():
    body = _body("async def review_script", "async def fix_script")
    assert "_library_prompt_context(step6)" in body
    assert '"pt_review_script.jinja"' in body


def test_fix_script_hands_the_library_to_its_prompt():
    body = _body("async def fix_script", "async def validate")
    assert "_library_prompt_context(step6)" in body
    assert '"pt_fix_script.jinja"' in body


# --- both templates render it as authoritative, only when present --------------------

def test_review_prompt_renders_the_library_as_an_authoritative_block():
    out = _render("pt_review_script.jinja", library_name="library_awptcm_t1.py", library_code=LIB)
    assert "## Helpers this script imports (authoritative" in out
    assert "from library_awptcm_t1 import *" in out
    assert LIB.strip() in out
    assert "false positive, not a defect" in out


def test_review_prompt_omits_the_block_without_a_library():
    out = _render("pt_review_script.jinja")
    assert "Helpers this script imports" not in out
    assert "```python\n\n```" not in out, "an empty fenced block would read as an empty library"


def test_fix_prompt_renders_the_library_and_forbids_fixing_a_correct_call():
    out = _render("pt_fix_script.jinja", library_name="library_awptcm_t1.py", library_code=LIB)
    assert "## Helpers this script imports (authoritative" in out
    assert LIB.strip() in out
    assert "must not be \"fixed\"" in out


def test_fix_prompt_omits_the_block_without_a_library():
    out = _render("pt_fix_script.jinja")
    assert "Helpers this script imports" not in out
