"""Step-6 naming: the default must be usable, and an edit must survive the page.

Three defects found together on 2026-08-31 (AWPTCM-T33351, group
'Authentication & Security (42)'). Each one alone would have been invisible; together
they made an edited Group field look accepted while everything server-side still saw
the default:

  1. `_group_display` stripped only the '(42)' count, so the value the API handed the
     browser to seed the Group field — and used as generate_script's own default —
     still contained '&', which `_validate_naming` rejects. The server offered a
     default its own validator refused, and the dry-run provenance render 400'd with
     "Invalid group name" before any prompt was built.
  2. step6.naming had exactly two writers: the SUCCESS tail of generate_script, and
     save_script, which 409s until a generated file exists. Before a first successful
     generation nothing would store the fields at all, so renderPtGenPanel's
     `naming.group || group_display` re-seed silently replaced an edit with the
     (invalid) default whenever the panel was navigated away from and back.
  3. A generation that FAILED discarded the reviewer's typed naming with it, because
     naming was written only after the model answered.

Pinned here: the sanitiser is identity on names that already validate (so existing
generated/ directories are untouched), every default it produces validates, naming
persists without a generated file, and a failed generation keeps it.

Offline: no network, no LLM. Real module + real app via TestClient, isolated ck.db.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
for _p in (REPO / "ask-ck" / "CK-main", REPO / "ask-ck" / "CK-main" / "CK_server"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


@pytest.fixture
def pc():
    from routers import pytest_create as mod
    return mod


# --- 1. the default the UI is handed must be one the validator accepts -------

@pytest.mark.parametrize("group_dir", [
    "Authentication & Security (42)",   # the case that exposed this
    "Management (71)",
    "Port (7)",
    "A&B",
    "Foo / Bar (3)",
    "***",
])
def test_every_group_display_default_passes_validation(pc, group_dir):
    """The exact composition generate_script uses when the body carries no group."""
    shown = pc._group_display(group_dir)
    pc._validate_naming(shown, "some_name")     # must not raise


def test_the_reported_group_becomes_what_a_human_typed(pc):
    assert pc._group_display("Authentication & Security (42)") == "Authentication_Security"


@pytest.mark.parametrize("group_dir,expected", [
    ("Management (71)", "Management"),
    ("Port (7)", "Port"),
    ("Port Security", "Port Security"),      # spaces are legal — must NOT be rewritten
    ("Already_Fine-1 (2)", "Already_Fine-1"),
])
def test_valid_groups_are_returned_unchanged(pc, group_dir, expected):
    """Existing generated/ directories must not be renamed by this change."""
    assert pc._group_display(group_dir) == expected


def test_sanitising_is_idempotent(pc):
    once = pc._group_display("Authentication & Security (42)")
    assert pc._group_display(once) == once


# --- 2. naming persists with no generated file ------------------------------

def _seed(key, **steps):
    from routers.pytest_create import pt_sessions
    from models import PtSession
    pt_sessions[key] = PtSession(key=key, group="Authentication & Security (42)", **steps)
    return pt_sessions[key]


@pytest.fixture
def cleanup():
    from routers.pytest_create import pt_sessions
    made = []
    yield made.append
    for k in made:
        pt_sessions.pop(k, None)


def test_naming_saves_before_any_generation_exists(client, cleanup):
    """The reported symptom: navigating away lost the edit, because nothing stored it."""
    key = "AWPTCM-TNAMINGONLY"
    cleanup(key)
    _seed(key)
    r = client.post(f"/api/pytest-create/save_naming/{key}",
                    headers={"X-CK-Session": "gate-test"},
                    json={"group": "Authentication_Security", "name": "802_1x-single-host"})
    assert r.status_code == 200, r.text
    assert r.json()["naming"] == {"group": "Authentication_Security",
                                  "name": "802_1x-single-host"}
    # and it is on the session the next render would read
    from routers.pytest_create import pt_sessions
    assert pt_sessions[key].step6["naming"]["group"] == "Authentication_Security"


def test_save_naming_still_validates(client, cleanup):
    key = "AWPTCM-TNAMINGBAD"
    cleanup(key)
    _seed(key)
    r = client.post(f"/api/pytest-create/save_naming/{key}",
                    headers={"X-CK-Session": "gate-test"},
                    json={"group": "Authentication & Security", "name": "x"})
    assert r.status_code == 400
    assert "Invalid group name" in r.json()["detail"]


def test_save_naming_refuses_once_a_script_exists(client, cleanup):
    """Renaming a generated script must move the file — that is save_script's job."""
    key = "AWPTCM-TNAMINGFILE"
    cleanup(key)
    _seed(key, step6={"naming": {"group": "Port", "name": "old"},
                      "files": {"test": {"name": "old.py", "code": "x = 1\n"}}})
    r = client.post(f"/api/pytest-create/save_naming/{key}",
                    headers={"X-CK-Session": "gate-test"},
                    json={"group": "Port", "name": "renamed"})
    assert r.status_code == 409
    assert "Save to generated/" in r.json()["detail"]


# --- 3. a failed generation must not take the naming with it ----------------

def test_naming_is_persisted_before_the_llm_call(pc):
    """Source-level pin: the write must precede the prompt/run_prompt call.

    Behavioural coverage would need a failing LLM; what actually matters is the
    ORDER, and that is exactly what regressed — naming was written only on the
    success path at the tail of the function.
    """
    import inspect
    src = inspect.getsource(pc.generate_script)
    write = src.index('_pre["naming"] = {"group": group, "name": name}')
    call = src.index("run_prompt")
    assert write < call, "naming must be persisted BEFORE the generation is attempted"


def test_a_dry_run_preview_does_not_write_the_session(pc):
    """Refresh (no send) renders a prompt; it must not persist anything.

    The naming pre-persist above sits before the LLM call, which is also before the
    dry-run return — so without an explicit guard, merely LOOKING at the prompt would
    have started writing to the session (and, on the live server, to the permanent
    ck.db). Order pin, for the same reason as the test above.
    """
    import inspect
    src = inspect.getsource(pc.generate_script)
    line = next(l for l in src.splitlines() if '_pre.get("naming")' in l)
    assert "not dry_run" in line, "the naming pre-persist must be skipped on a dry run"
