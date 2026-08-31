"""Regression pins for the testbox-profile field contract (`pt_exec.normalize_profile`).

Written 2026-09-01 with the Testboxes panel facelift. Two things are pinned:

1. `user` is REQUIRED and has NO default. It used to default to "st-art", which is
   wrong on at least one live bench — `st-art@tb470` answers `Permission denied
   (publickey,password)` while `terrenceb@tb470` authenticates (TESTBOX-ACCESS.md 3a).
   A wrong-by-default username fails at the SSH layer, so it presents as a network or
   testbox fault rather than as a profile mistake. The whole point of the change is
   that the failure can no longer be reached by *omission*, so the pin has to assert
   the absence of the default as well as the presence of the requirement.

2. The form asks for every field the server requires. The panel is the only way most
   people will create a profile, so a server-required field missing from the form is
   an unfillable form, and a form field the server ignores is noise. This is the
   check the facelift was asked for ("only asking for fields that are absolutely
   required"), so it is guarded rather than left to review.

Pure unit tests — no DB, no network, no hardware, no LLM.
"""
import re
from pathlib import Path

import pytest

import pt_exec

REPO = Path(__file__).resolve().parents[1]
INDEX_HTML = REPO / "ask-ck" / "CK-main" / "CK_server" / "static" / "index.html"
PYTEST_JS = REPO / "ask-ck" / "CK-main" / "CK_server" / "static" / "js" / "pytest.js"


def _body(**over):
    """A minimal profile body that normalizes cleanly, before any mutation."""
    base = {"name": "tb470", "tb_number": "470", "host": "tb470", "user": "terrenceb"}
    base.update(over)
    return base


# ----------------------------------------------------------------- user is required


def test_user_is_required():
    with pytest.raises(ValueError) as e:
        pt_exec.normalize_profile(_body(user=""))
    assert "user" in str(e.value)


def test_user_missing_entirely_is_rejected():
    body = _body()
    del body["user"]
    with pytest.raises(ValueError) as e:
        pt_exec.normalize_profile(body)
    assert "user" in str(e.value)


def test_user_has_NO_default():
    """The heart of it: if a default ever comes back, omitting `user` silently
    succeeds again and the SSH-layer failure returns."""
    assert pt_exec.PROFILE_DEFAULTS.get("user") is None
    assert "user" in pt_exec.PROFILE_REQUIRED


def test_st_art_is_not_reintroduced_as_a_default():
    assert pt_exec.PROFILE_DEFAULTS.get("user") != "st-art"


def test_a_complete_profile_still_normalizes():
    prof = pt_exec.normalize_profile(_body())
    assert prof["user"] == "terrenceb"
    assert prof["host"] == "tb470"
    # the untouched defaults must survive the change
    assert prof["port"] == 22
    assert prof["auth"] == "key"
    assert prof["framework_path"] == "/home/st-art/framework"
    assert prof["remote_workdir"] == "/home/st-art/pytest-create"


def test_the_other_required_fields_are_unchanged():
    for field in ("tb_number", "host"):
        body = _body()
        del body[field]
        with pytest.raises(ValueError) as e:
            pt_exec.normalize_profile(body)
        assert field in str(e.value)


def test_the_error_names_every_missing_field_at_once():
    """A one-at-a-time error makes filling the form a guessing game."""
    with pytest.raises(ValueError) as e:
        pt_exec.normalize_profile({"name": "x"})
    msg = str(e.value)
    for field in pt_exec.PROFILE_REQUIRED:
        assert field in msg


# -------------------------------------------------- the form matches the contract


def _form_required_ids():
    """Field ids the panel marks required, read from the rendered markup."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    panel = html[html.index('id="panel-pt-testbox"'):html.index("</main>")]
    # a required field is a label carrying <span class="tb-req"> whose `for` names the input
    return set(re.findall(r'<label class="tb-label" for="([^"]+)">[^<]*<span class="tb-req">', panel))


def test_the_form_asks_for_every_server_required_field():
    ids = _form_required_ids()
    assert ids, "no required-marked fields parsed out of the panel — has it been reshaped?"
    id_for = {"tb_number": "pt-tb-number", "host": "pt-tb-host", "user": "pt-tb-user"}
    for field in pt_exec.PROFILE_REQUIRED:
        assert id_for[field] in ids, (
            f"server requires {field!r} but the form does not mark {id_for[field]} required")


def test_the_form_and_the_js_agree_on_what_is_required():
    """The visible asterisks and the save-time validation must be the same set, or the
    form either blocks on an unmarked field or accepts a marked one."""
    js = PYTEST_JS.read_text(encoding="utf-8")
    start = js.index("const PT_TB_REQUIRED")
    block = js[start:js.index("];", start)]
    assert set(re.findall(r"\['([a-z0-9-]+)',", block)) == _form_required_ids()


def test_the_js_no_longer_defaults_the_user_to_st_art():
    """The frontend used to send `|| 'st-art'`, which would defeat the server-side
    requirement by always supplying a value."""
    js = PYTEST_JS.read_text(encoding="utf-8")
    save = js[js.index("async function ptSaveProfile()"):js.index("async function ptDeleteProfile")]
    assert "st-art" not in save
