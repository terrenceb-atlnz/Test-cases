"""The generate prompt must not instruct the model to do what the lint rejects.

PHASE 7.8. The only lint ERROR that has ever fired on a real generation was on T44297 — the
best script we have produced:

    line 273: calls setup.init_portlink() directly, which skips the run-time MEDIA assertion.

The model was following instructions. The prompt told it to *"bind every device you use in
`TestSet.init`"* and pointed it at `init_portlink()`, while the skeleton's `init()` is FIXED
FRAME that already binds everything through `_ck_bind_link()` and says "do not edit or
delete". `_ck_bind_link` appeared in the prompt **zero times**. So the prompt demanded the
one thing the lint forbids, and the lint then failed the model for complying.

That is the shape to prevent: a rule enforced in code that no instruction ever conveyed. A
lint whose only real-world firing is caused by our own prompt is not catching a model defect,
it is manufacturing one — and it makes the artefact permanently unconfirmable.
"""
import ast
import pathlib
import re

import pytest

from _prose import code_lines, flat, expand_includes

REPO = pathlib.Path(__file__).resolve().parents[1]
SERVER = REPO / "ask-ck" / "CK-main" / "CK_server"
# The prompt AS SENT is the template with its includes resolved — the fill
# rules live in pt_fill_rules.jinja since 2026-09-02, shared with the per-unit
# prompt. Reading the bare file would assert about half the prompt.
class _Expanded:
    def __init__(self, path):
        self.path = path
    def read_text(self, *a, **k):
        return expand_includes(self.path)
    def __truediv__(self, other):
        return self.path / other

GENERATE = _Expanded(SERVER / "templates" / "prompts" / "pt_generate_script.jinja")
SKELETON = SERVER / "templates" / "pt_script_template.py.jinja"
ROUTER = SERVER / "routers" / "pytest_create.py"

PROMPT = GENERATE.read_text(encoding="utf-8")
FRAME = SKELETON.read_text(encoding="utf-8")


# --------------------------------------------------- the prompt must not demand the forbidden

def test_prompt_does_not_tell_the_model_to_bind_devices_in_init():
    """The instruction that produced the only real lint error."""
    assert "bind every device you use" not in flat(PROMPT), (
        "the prompt still tells the model to bind devices in TestSet.init, which the fixed "
        "frame already does and forbids editing")


def test_prompt_tells_the_model_init_is_fixed_frame():
    body = flat(PROMPT).lower()
    assert "fixed frame" in body, \
        "the prompt must say init() is fixed frame, or the model will fill it"


def test_prompt_never_directs_the_model_to_call_init_portlink():
    """`init_portlink()` is the frame's business. Every mention must forbid, not instruct."""
    offenders = []
    for i, line in enumerate(PROMPT.splitlines(), 1):
        if "init_portlink" not in line:
            continue
        window = " ".join(PROMPT.splitlines()[max(0, i - 4):i + 3]).lower()
        if not any(w in window for w in ("never", "do not", "fixed frame", "yourself")):
            offenders.append(f"{i}: {line.strip()[:90]}")
    assert not offenders, (
        "these prompt lines reference init_portlink() without forbidding it — the model will "
        "read them as instructions:\n  " + "\n  ".join(offenders))


def test_prompt_explains_why_the_frames_binding_matters():
    """A rule with no reason gets reasoned around; this one has a real consequence."""
    body = flat(PROMPT).lower()
    assert "media" in body and "_ck_bind_link" in PROMPT, (
        "the prompt must name _ck_bind_link and say what bypassing it costs (the media "
        "assertion), so the rule survives a model that reasons about it")


# ------------------------------------------------------------- the frame is genuinely fixed

def test_the_skeleton_frame_really_does_bind_everything():
    """If this stops being true, rule 3 becomes wrong in the other direction."""
    assert "_ck_bind_link" in FRAME
    assert "Fixed frame" in FRAME


def test_the_frames_init_is_not_a_fill_slot():
    """`init()` must contain no FILL marker, or the prompt is right to fill it."""
    init_at = FRAME.index("def init(self, setup):")
    nxt = FRAME.find("\n    def ", init_at + 10)
    init_body = FRAME[init_at:nxt if nxt > 0 else len(FRAME)]
    assert ">>>" not in init_body, \
        "init() carries a FILL marker, so it is not fixed frame after all"


# ------------------------------------------------- every lint error must be conveyable
#
# The generalisation. A lint error the prompt never mentions is a trap: the model cannot
# comply with a rule it was not given, and the reviewer cannot confirm the result.

_LINT_RULES_NEEDING_PROMPT_SUPPORT = {
    # lint error fragment -> a term the prompt must contain to have conveyed it
    "init_portlink": "_ck_bind_link",
    "unfilled template placeholder": "FILL",
    "has no self.log()": "self.log",
    "missing ts.run(sys.argv)": "ts.run",
}


@pytest.mark.parametrize("lint_fragment,prompt_term",
                         sorted(_LINT_RULES_NEEDING_PROMPT_SUPPORT.items()))
def test_each_enforced_rule_is_conveyed_by_the_prompt(lint_fragment, prompt_term):
    """The lint enforces it, so the prompt must have asked for it."""
    router = ROUTER.read_text(encoding="utf-8")
    assert lint_fragment in router, \
        f"lint no longer checks {lint_fragment!r} — drop it from this mapping"
    assert prompt_term in PROMPT, (
        f"the lint rejects {lint_fragment!r} but the generate prompt never mentions "
        f"{prompt_term!r} — the model is being failed for a rule it was never given")
