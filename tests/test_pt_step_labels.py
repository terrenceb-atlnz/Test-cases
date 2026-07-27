"""The PyTest Creator step gates must name steps the way the UI does.

The internal `stepN` session keys and the numbers on screen DIVERGED when the old
step 4 (Fit Decision) was folded into Fragments:

    internal step5  ->  "4. Fragments"   (badge id pt-badge-5)
    internal step6  ->  "5. Generate"    (badge id pt-badge-6)

Quoting the raw key in a 409 was actively misleading: a user blocked on Fragments was
told "Generation requires step5 to be confirmed first", and step5 is the number the UI
puts on *Generate* — i.e. the message named the very step they were trying to run.

These pin the mapping against the real index.html so a future renumber breaks a test
instead of silently producing wrong error messages again.
"""
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
INDEX_HTML = REPO / "ask-ck" / "CK-main" / "CK_server" / "static" / "index.html"

sys.path.insert(0, str(REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(REPO / "ask-ck" / "CK-main" / "CK_server"))

pt = pytest.importorskip("CK_server.routers.pytest_create")


def test_step5_is_fragments_not_generate():
    """The exact confusion that prompted the fix."""
    assert pt._step_label("step5") == "4. Fragments"
    assert "Generate" not in pt._step_label("step5")


def test_step6_is_generate():
    assert pt._step_label("step6") == "5. Generate"


def test_accepts_both_a_key_and_a_bare_number():
    # _require_confirmed passes 'step5'; confirm_step passes the int 5 from the URL.
    assert pt._step_label("step5") == pt._step_label(5)
    assert pt._step_label(7) == "6. Run"


def test_unmapped_step_degrades_to_the_raw_value():
    """An unknown step must not raise inside an error path."""
    assert pt._step_label(99) == "99"
    assert pt._step_label("stepX") == "stepX"


def test_folded_away_step4_still_has_a_name():
    """Internal step4 (Fit Decision) has no panel but is still reachable via
    confirm_step/{key}/4 — it must not surface as a bare number."""
    assert pt._step_label(4) != "4"
    assert "Fragments" in pt._step_label(4)


def test_no_gate_message_leaks_a_raw_internal_key():
    src = (REPO / "ask-ck" / "CK-main" / "CK_server" / "routers" / "pytest_create.py").read_text()
    # every 409 gate message should route through _step_label, never interpolate stepN
    for m in re.finditer(r'f"[^"]*requires \{step_key\}[^"]*"', src):
        pytest.fail(f"gate message interpolates the raw internal key: {m.group(0)}")
    for m in re.finditer(r'f"Nothing to confirm yet for step \{step\}', src):
        pytest.fail(f"confirm message interpolates the raw step number: {m.group(0)}")


@pytest.mark.skipif(not INDEX_HTML.exists(), reason="index.html not present")
def test_mapping_matches_the_real_ui_headings():
    """Ground the table against the actual UI rather than trusting the constant.

    Each panel renders `PyTest Creator — <label> <span id="pt-badge-<internal>">`, which
    ties the on-screen label to the internal step number directly.
    """
    html = INDEX_HTML.read_text()
    found = dict(
        (f"step{internal}", label.strip())
        for label, internal in re.findall(
            r'PyTest Creator — (.+?)\s*<span id="pt-badge-(\d+)"', html)
    )
    assert found, "could not parse any PyTest Creator panel headings from index.html"
    for key, ui_label in found.items():
        assert pt._step_label(key) == ui_label, (
            f"{key}: code says {pt._step_label(key)!r}, UI shows {ui_label!r}")
