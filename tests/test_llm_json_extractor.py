"""Regression tests for the llm.py JSON-parser hardening (2026-07-27e).

The 5 ad-hoc greedy-regex / brace-counting parse sites (extract_json_block's fence-first +
depth-in-strings bugs; parse_llm_to_structured, _parse_suggest_id_list, analyze_atp_coverage
greedy regexes) now route through one string-aware extract_json_block. These pin its behavior.

Pure unit tests — no network, no LLM call.
"""
import llm

E = llm.extract_json_block


def test_brackets_inside_string_values_do_not_break_parsing():
    # The old depth counter counted this '}' inside the string and closed early -> None.
    assert E('{"desc": "use { and ] inside a string"}') == {"desc": "use { and ] inside a string"}


def test_escaped_quote_and_brace_in_string():
    assert E('{"note": "has a \\" quote and } brace"}') == {"note": 'has a " quote and } brace'}


def test_picks_the_fenced_block_that_actually_parses():
    # An illustrative non-JSON fence precedes the real one; must return the real JSON.
    content = '```\nnot json here\n```\n```json\n[{"id":"A"}]\n```'
    assert E(content) == [{"id": "A"}]


def test_prose_brace_before_real_array_is_skipped():
    # A greedy regex latched onto the prose brace; the string-aware position scan skips it.
    assert E('prose { not json } then [{"description":"x"}]') == [{"description": "x"}]


def test_object_with_nested_array_returns_the_outer_object():
    # Must NOT return the inner per_step array.
    assert E('{"decision":"new","per_step":[1,2,3]}') == {"decision": "new", "per_step": [1, 2, 3]}


def test_leading_prose_before_array():
    assert E('here is the answer:\n[{"id":"A","reason":"r"},{"id":"B"}]') == \
        [{"id": "A", "reason": "r"}, {"id": "B"}]


def test_no_json_returns_none():
    assert E("no json at all") is None
    assert E("") is None
    assert E(None) is None


# --- the downstream parsers that route through the extractor --------------------
def test_parse_llm_to_structured_extracts_steps_with_braces_in_text():
    # A step description containing a brace must not drop the whole array.
    out = llm.parse_llm_to_structured(
        '[{"description":"set mtu to {value}","expectedResult":"ok"},'
        '{"description":"verify","expectedResult":""}]',
        "AWPTCM-T1",
    )
    descs = [s["description"] for s in out["testScript"]["steps"]]
    assert "set mtu to {value}" in descs and "verify" in descs


def test_suggest_id_list_handles_object_wrapped_array():
    out = llm._parse_suggest_id_list('{"suggestions":[{"id":"ART-1","reason":"r"}]}')
    assert out and out[0]["id"] == "ART-1"


def test_suggest_id_list_plain_array_with_leading_prose():
    out = llm._parse_suggest_id_list('sure:\n[{"id":"ART-2"}]')
    assert out and out[0]["id"] == "ART-2"
