#!/usr/bin/env python3
"""PyTest Creator — Part 3a mechanical grader (PLAN-pytest-testing.md §3, criteria 1-3 + the
offline half of 6).

Reads a case's generated script + confirmed step2/step5 state straight from `ck.db` and
emits a per-case mechanical report. No LLM, no network, no hardware — this is the ground
truth both LLM judges and the human review see alongside their own verdicts.

Criteria (rubric in PLAN §3, conformance rules in TEMPLATE-SPEC.md):
  C1 template used        exactly / partially / not at all
  C2 snippets used        exactly / partially / not at all
  C3 snippet order        right / wrong / n-a
  C6 logging contract     yes / partial / no   (offline half only; the on-hardware
                          half needs a real tb470 run — Part 3b, currently blocked)

Deliberately NOT graded here: criterion 4 (gap-fill quality — the LLM judges' job) and
criterion 5 (executes — needs tb470).

Usage:
  python3 tool/pt_grade.py                      # all pt sessions with a generated script
  python3 tool/pt_grade.py AWPTCM-T33234        # one case
  python3 tool/pt_grade.py --json               # machine-readable to stdout
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "ask-ck" / "var" / "ck.db"

# Import the SERVER's own helpers so grading can never drift from generation.
# Both dirs are needed: the package root for `CK_server.*`, and CK_server itself
# because its modules import siblings flat (`from models import ...`).
sys.path.insert(0, str(REPO / "ask-ck" / "CK-main"))
sys.path.insert(0, str(REPO / "ask-ck" / "CK-main" / "CK_server"))
from CK_server.routers.pytest_create import (  # noqa: E402
    _step_kind, _fragment_tag, _frag_key,
)
from CK_server.routers import pytest_create as _pt  # noqa: E402


def _is_provenance_echo(line: str) -> bool:
    """Is this line a model-emitted provenance tag/restatement?

    The generator's echo detection is actively being reworked (a single catch-all
    `_PROVENANCE_ECHO_RX` vs. a narrower `_is_provenance_echo` split into tag-shape +
    "provenance tag/:" phrasing). Bind to whichever the router currently exposes rather
    than importing one private name — grading must not break because the generator's
    internals moved, and an echo miscount only affects an advisory field.
    """
    fn = getattr(_pt, "_is_provenance_echo", None)
    if fn is not None:
        return bool(fn(line))
    rx = getattr(_pt, "_PROVENANCE_ECHO_RX", None)
    if rx is not None:
        return bool(rx.match(line))
    return bool(_TAG_RX.match(line))                    # last-resort local fallback

# A tag line the restamp pass wrote, e.g. "# ART 1363_ipv6/test.py lines 55-78" / "# AI vllm-fast 2026-07-27".
_TAG_RX = re.compile(r"^\s*#\s*(ART|SVT|legacy|AI)\b(.*)$", re.IGNORECASE)


# --------------------------------------------------------------------------- data


def load_case(conn: sqlite3.Connection, case_key: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT payload FROM sessions WHERE kind='pt' AND case_key=?", (case_key,)
    ).fetchone()
    if not row or not row[0]:
        return None
    return json.loads(row[0])


def all_case_keys(conn: sqlite3.Connection) -> List[str]:
    return [r[0] for r in conn.execute(
        "SELECT case_key FROM sessions WHERE kind='pt' ORDER BY case_key")]


def script_of(payload: dict) -> Tuple[str, str]:
    """(filename, code) of the generated test script, or ('','')."""
    test = ((payload.get("step6") or {}).get("files") or {}).get("test") or {}
    return test.get("name") or "", test.get("code") or ""


def selected_fragments(payload: dict) -> List[dict]:
    """The fragments generation ACTUALLY used — mirrors the server's
    `_selected_fragments`. step5.fragments is the full gathered pool; step5.selected is
    the reviewer's chosen subset, and Generate reads only that. Grading the whole pool
    would expect tags for fragments that were never offered to the model.
    """
    step5 = payload.get("step5") or {}
    pool = step5.get("fragments") or []
    if "selected" not in step5:
        return list(pool)
    sel = step5.get("selected") or []
    sel_keys = {tuple(s) if isinstance(s, (list, tuple))
                else (s.get("source_id"), s.get("symbol")) for s in sel}
    return [f for f in pool if _frag_key(f) in sel_keys]


# --------------------------------------------------------------------------- parsing


def testcase_classes(tree: ast.AST) -> List[ast.ClassDef]:
    """TestCase_<n> classes in source order (the order they appear IS the run order the
    __main__ block should mirror; C1 checks that separately)."""
    out = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and re.fullmatch(r"TestCase_\d+", node.name):
            out.append(node)
    return sorted(out, key=lambda c: int(c.name.split("_")[1]))


def testset_class(tree: ast.AST) -> Optional[ast.ClassDef]:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "TestSet":
            return node
    return None


def method(cls: ast.ClassDef, name: str) -> Optional[ast.FunctionDef]:
    return next((n for n in cls.body
                 if isinstance(n, ast.FunctionDef) and n.name == name), None)


def class_attrs(cls: ast.ClassDef) -> Dict[str, object]:
    out: Dict[str, object] = {}
    for n in cls.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            out[n.targets[0].id] = getattr(n.value, "value", None)
    return out


def self_calls(fn: ast.FunctionDef, meth: str) -> List[ast.Call]:
    return [n for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == meth and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "self"]


def main_body_source(code: str, fn: ast.FunctionDef) -> str:
    return ast.get_source_segment(code, fn) or ""


def leading_tag(code: str, fn: ast.FunctionDef) -> Optional[str]:
    """The FIRST provenance tag inside main().

    `_restamp_provenance` guarantees the authoritative tag is inserted as the first line
    of the body, so we read that one and ignore any later model echo (observed on
    T33235: the model restated the prompt's instruction below a self.log() call, which
    the restamp's leading-run strip does not reach). Reading the first tag makes the
    grade immune to that cosmetic duplication.
    """
    src = main_body_source(code, fn).split("\n")
    for line in src[1:]:                       # skip the `def main(self):` line
        if not line.strip():
            continue
        m = _TAG_RX.match(line)
        return line.strip() if m else None     # first non-blank line decides
    return None


def echo_tag_count(code: str, fn: ast.FunctionDef) -> int:
    """How many provenance-echo comment lines are in this main() (>1 == leftover echo).

    Uses the server's own `_is_provenance_echo` so this tracks the generator's definition
    of an echo. That definition was deliberately narrowed (a bare tag, or the prompt's
    "provenance tag"/"provenance:" phrasing) after the original catch-all regex was found
    to delete real commentary that merely mentioned SVT/legacy.
    """
    src = main_body_source(code, fn).split("\n")[1:]
    return sum(1 for l in src if _is_provenance_echo(l))


# --------------------------------------------------------------------------- criteria


def grade_c1(code: str, tree: ast.AST, sequence: List[dict], case_key: str) -> dict:
    """C1 — template used. TEMPLATE-SPEC.md: fixed frame present, one TestCase per
    verify step, __main__ adds every case in order and calls ts.run(sys.argv)."""
    findings: List[str] = []
    ts = testset_class(tree)
    cases = testcase_classes(tree)

    if ts is None:
        findings.append("no TestSet class")
    else:
        for m in ("init", "configure", "tear_down"):
            if method(ts, m) is None:
                findings.append(f"TestSet.{m}() missing")
        if not any(isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "FEATURES"
                   for n in ts.body if isinstance(n, ast.Assign) and n.targets):
            findings.append("TestSet.FEATURES missing")

    if not cases:
        findings.append("no TestCase_<n> classes")

    # one TestCase per VERIFY step (setup steps render into TestSet.configure instead)
    verify_steps = [s for s in sequence if _step_kind(s) != "setup"] or list(sequence)
    expected = len(verify_steps)
    if expected and len(cases) != expected:
        findings.append(f"{len(cases)} TestCase classes vs {expected} verify steps")

    # contiguous numbering 1..N
    nums = [int(c.name.split("_")[1]) for c in cases]
    if nums and nums != list(range(1, len(nums) + 1)):
        findings.append(f"TestCase numbering not contiguous 1..N: {nums}")

    # __main__ footer: every case added, in order, then ts.run(sys.argv)
    footer = re.search(r"if __name__ == ['\"]__main__['\"]:(.*)\Z", code, re.S)
    if not footer:
        findings.append("no __main__ block")
    else:
        blk = footer.group(1)
        added = re.findall(r"add_testCase\(\s*(TestCase_\d+)\s*\(", blk)
        if added != [c.name for c in cases]:
            findings.append(f"__main__ add order {added} != class order {[c.name for c in cases]}")
        if not re.search(r"\.run\(\s*sys\.argv\s*\)", blk):
            findings.append("__main__ missing ts.run(sys.argv)")

    # per-case required attributes (testCaseRef must be the case key)
    for c in cases:
        attrs = class_attrs(c)
        for req in ("testCaseDesc", "testCaseRef", "testCaseMethod"):
            if req not in attrs:
                findings.append(f"{c.name}.{req} missing")
        if attrs.get("testCaseRef") not in (None, case_key):
            findings.append(f"{c.name}.testCaseRef={attrs.get('testCaseRef')!r} != {case_key!r}")
        if method(c, "main") is None:
            findings.append(f"{c.name}.main() missing")
        if method(c, "tear_down") is None:
            findings.append(f"{c.name}.tear_down() missing")

    frame_broken = any("no TestSet" in f or "no TestCase" in f for f in findings)
    if frame_broken:
        verdict = "not at all"
    elif findings:
        verdict = "partially"
    else:
        verdict = "exactly"
    return {"verdict": verdict, "testcase_classes": len(cases),
            "verify_steps": expected, "findings": findings}


def _normalize(s: str) -> str:
    """Whitespace/comment-insensitive form for substring matching."""
    lines = []
    for l in s.split("\n"):
        l = re.sub(r"#.*$", "", l).strip()
        if l:
            lines.append(re.sub(r"\s+", " ", l))
    return "\n".join(lines)


def grade_c2_c3(code: str, tree: ast.AST, fragments: List[dict],
                sequence: List[dict]) -> Tuple[dict, dict]:
    """C2 snippet reuse + C3 snippet order.

    Reuse is measured two independent ways and both are reported:
      - TAG evidence: the authoritative provenance stamp on each main() (PLAN §1.5 says
        the tags ARE the reuse evidence, and they're server-stamped so can't be faked).
      - CODE evidence: normalized line overlap between the fragment and the main() body,
        which catches a block that was tagged but then rewritten beyond recognition.
    """
    cases = testcase_classes(tree)
    if not fragments:
        return ({"verdict": "n-a", "reason": "no fragments selected (decision: new)",
                 "per_step": []},
                {"verdict": "n-a", "reason": "no fragments to order", "expected": [], "actual": []})

    # fragment maps_to uses ORIGINAL step numbers; TestCase_<n> uses contiguous class
    # numbers after setup steps drop out. Rebuild the same remap _restamp_provenance uses.
    verify_steps = [s for s in sequence if _step_kind(s) != "setup"] or list(sequence)
    orig_to_class: Dict[int, int] = {}
    for new_i, s in enumerate(verify_steps, 1):
        try:
            orig_to_class[int(s.get("n"))] = new_i
        except (TypeError, ValueError):
            continue

    expected_tag_by_class: Dict[int, str] = {}
    frag_by_class: Dict[int, dict] = {}
    for f in fragments:
        tag = _fragment_tag(f.get("source_id", ""), f.get("loc"), f.get("py2_translated", False))
        for n in f.get("maps_to") or []:
            try:
                cls_n = orig_to_class.get(int(n), int(n))
            except (TypeError, ValueError):
                continue
            expected_tag_by_class[cls_n] = tag
            frag_by_class[cls_n] = f

    per_step = []
    tag_ok = tag_total = 0
    for c in cases:
        n = int(c.name.split("_")[1])
        fn = method(c, "main")
        if fn is None:
            continue
        actual = leading_tag(code, fn)
        expected = expected_tag_by_class.get(n)
        body = main_body_source(code, fn)

        overlap = None
        if n in frag_by_class:
            frag_lines = [l for l in _normalize(frag_by_class[n].get("code") or "").split("\n") if len(l) > 8]
            body_norm = _normalize(body)
            if frag_lines:
                hit = sum(1 for l in frag_lines if l in body_norm)
                overlap = round(hit / len(frag_lines), 3)

        if expected:
            tag_total += 1
            match = (actual == expected)
            if match:
                tag_ok += 1
        else:
            match = None                        # gap-fill step: no fragment expected

        per_step.append({
            "testcase": c.name,
            "expected_tag": expected,
            "actual_tag": actual,
            "tag_matches": match,
            "is_gap_fill": expected is None,
            "code_overlap": overlap,
            "duplicate_tag_lines": echo_tag_count(code, fn),
        })

    # Stale-artifact detection. Every stamped tag is authoritative for the fragment set
    # that was live AT GENERATION TIME. If none of the tags in the script names any
    # currently-selected fragment, the script predates a later step5 change — the
    # mismatch is provenance drift, NOT the model ignoring its snippets. Scoring that as
    # "not at all" would blame the generator for the reviewer's later edit.
    stamped = {p["actual_tag"] for p in per_step if p["actual_tag"]}
    current = set(expected_tag_by_class.values())
    if tag_total and stamped and not (stamped & current) and not any(
            t.startswith("# AI") for t in stamped & current):
        real_tags = {t for t in stamped if not t.startswith("# AI")}
        if real_tags and not (real_tags & current):
            return ({"verdict": "stale",
                     "reason": "the script's provenance tags reference a fragment "
                               "selection that no longer matches step5 — it was "
                               "generated before the selection changed. Regenerate "
                               "before grading C2/C3.",
                     "stamped_tags": sorted(real_tags),
                     "current_tags": sorted(t for t in current if not t.startswith("# AI")),
                     "per_step": per_step},
                    {"verdict": "n-a", "reason": "C2 is stale; order is not meaningful",
                     "expected": [], "actual": []})

    if tag_total == 0:
        c2 = {"verdict": "n-a", "reason": "no fragment maps to any TestCase", "per_step": per_step}
    elif tag_ok == tag_total:
        # Every step that should reuse a fragment is stamped with the right one, so the
        # snippets WERE used: "exactly" in rubric terms (criterion 2 asks whether the
        # snippets were used, not whether they were copied verbatim).
        #
        # `avg_code_overlap` is reported but deliberately does NOT downgrade the verdict.
        # Observed on T33234: the model correctly ADAPTS a fragment — same intent, but
        # rewritten into the template's bound device names and the mandatory logging
        # contract — which drives literal line overlap near zero while the reuse is
        # entirely genuine. Verbatim copying is not the goal (§1.4 leaves main() bodies
        # free), so a low overlap is a signal for the human/LLM judges to interpret, not
        # a mechanical failure.
        overlaps = [p["code_overlap"] for p in per_step if p["code_overlap"] is not None]
        avg = round(sum(overlaps) / len(overlaps), 3) if overlaps else None
        c2 = {"verdict": "exactly",
              "tags_matched": f"{tag_ok}/{tag_total}", "avg_code_overlap": avg,
              "overlap_note": "low overlap == adapted, not absent; see per_step. "
                              "Judges assess adaptation quality (criterion 4).",
              "per_step": per_step}
    elif tag_ok:
        c2 = {"verdict": "partially", "tags_matched": f"{tag_ok}/{tag_total}",
              "per_step": per_step}
    else:
        c2 = {"verdict": "not at all", "tags_matched": f"0/{tag_total}", "per_step": per_step}

    # C3 — do the reused fragments appear in sequence order?
    expected_order = [expected_tag_by_class[n] for n in sorted(expected_tag_by_class)]
    actual_order = [p["actual_tag"] for p in per_step
                    if p["expected_tag"] and p["actual_tag"]]
    # compare de-duplicated runs: one fragment legitimately spans several steps
    def dedup(seq):
        out = []
        for x in seq:
            if not out or out[-1] != x:
                out.append(x)
        return out
    c3 = {"verdict": "right" if dedup(actual_order) == dedup(expected_order) else "wrong",
          "expected": dedup(expected_order), "actual": dedup(actual_order)}
    return c2, c3


def grade_c6_offline(code: str, tree: ast.AST) -> dict:
    """C6 offline half — the logging contract inside every main().

    LOGGING-CONTRACT.md: step-start log, observed log, exactly one NON-EMPTY
    passed()/failed(). The standard if/else idiom has passed() in one branch and
    failed() in the other, so >=1 non-empty verdict is correct (mirrors _lint_generated).
    """
    cases = testcase_classes(tree)
    rows, bad = [], 0
    for c in cases:
        fn = method(c, "main")
        if fn is None:
            rows.append({"testcase": c.name, "ok": False, "why": "no main()"})
            bad += 1
            continue
        logs = self_calls(fn, "log")
        verdicts = self_calls(fn, "passed") + self_calls(fn, "failed")
        nonempty = [v for v in verdicts
                    if v.args and not (isinstance(v.args[0], ast.Constant)
                                       and str(v.args[0].value).strip() == "")]
        src = main_body_source(code, fn)
        has_step_start = bool(re.search(r"self\.log\(\s*['\"]?STEP\s*\d+", src))
        has_observed = bool(re.search(r"self\.log\(.*OBSERVED", src, re.S))
        why = []
        if len(logs) < 2:
            why.append(f"{len(logs)} self.log() (need step-start + observed)")
        if not has_step_start:
            why.append("no 'STEP <n>:' start log")
        if not has_observed:
            why.append("no 'OBSERVED:' evidence log")
        if not nonempty:
            why.append("no non-empty passed()/failed()")
        ok = not why
        if not ok:
            bad += 1
        rows.append({"testcase": c.name, "ok": ok, "n_log": len(logs),
                     "n_verdicts": len(verdicts), "n_nonempty": len(nonempty),
                     "why": why})
    if not rows:
        verdict = "no"
    elif bad == 0:
        verdict = "yes"
    elif bad < len(rows):
        verdict = "partial"
    else:
        verdict = "no"
    return {"verdict": verdict, "conformant": f"{len(rows) - bad}/{len(rows)}",
            "note": "offline half only — the on-hardware half needs a real tb470 run "
                    "(parse_framework_log over the run log); Part 3b is blocked.",
            "per_testcase": rows}


# --------------------------------------------------------------------------- report


def _caveats(payload: dict) -> List[str]:
    """Conditions that make a grade less trustworthy — surfaced so a reader never takes
    a verdict at face value when the artifact it grades is stale or unreviewed."""
    out: List[str] = []
    step5, step6 = payload.get("step5") or {}, payload.get("step6") or {}
    if not step5.get("confirmed"):
        out.append("step5 (fragments) is NOT confirmed — the reviewed-reuse gate was "
                   "never closed, so C2/C3 grade an unreviewed selection")
    if not step6.get("confirmed"):
        out.append("step6 (generate) is NOT confirmed")
    if step6.get("invalidated_at"):
        out.append(f"step6 was invalidated at {step6['invalidated_at']} — the script may "
                   "predate a later upstream change")
    model = ((step6.get("provenance") or {}).get("llm") or {}).get("model")
    if model in (None, "", "default"):
        out.append(f"generated by model={model!r} (a headless-CLI default, not the "
                   "workspace vLLM) — not comparable to the vllm-fast runs")
    return out


def grade_case(conn: sqlite3.Connection, case_key: str) -> dict:
    payload = load_case(conn, case_key)
    if payload is None:
        return {"case_key": case_key, "error": "no pt session"}
    fname, code = script_of(payload)
    if not code:
        return {"case_key": case_key, "error": "no generated script (step 6 not run)"}

    sequence = (payload.get("step2") or {}).get("sequence") or []
    fragments = selected_fragments(payload)
    pool_size = len((payload.get("step5") or {}).get("fragments") or [])
    step6 = payload.get("step6") or {}

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {"case_key": case_key, "error": f"script does not parse: {e}"}

    c1 = grade_c1(code, tree, sequence, case_key)
    c2, c3 = grade_c2_c3(code, tree, fragments, sequence)
    c6 = grade_c6_offline(code, tree)

    return {
        "case_key": case_key,
        "script": {"name": fname, "chars": len(code),
                   "generated_by": (step6.get("provenance") or {}).get("llm"),
                   "iterations": step6.get("iterations"),
                   "lint_ok": (step6.get("lint") or {}).get("ok")},
        "inputs": {"sequence_steps": len(sequence),
                   "verify_steps": c1["verify_steps"],
                   "fragments_selected": len(fragments),
                   "fragments_pool": pool_size,
                   "fit_decision": (payload.get("step4") or {}).get("decision")},
        "caveats": _caveats(payload),
        "criteria": {
            "1_template_used": c1,
            "2_snippets_used": c2,
            "3_snippet_order": c3,
            "6_logging_contract_offline": c6,
        },
        "blocked": {
            "4_gap_fill_quality": "LLM judges + human review (not mechanical)",
            "5_code_executes": "BLOCKED — needs a real tb470 run; configs/tb470.setup "
                               "does not exist yet (physical topology prerequisite)",
            "6_logging_on_hardware": "BLOCKED — same tb470 prerequisite",
        },
    }


def print_report(r: dict) -> None:
    if r.get("error"):
        print(f"  {r['case_key']}: ERROR — {r['error']}")
        return
    s, i, c = r["script"], r["inputs"], r["criteria"]
    llm = s.get("generated_by") or {}
    print(f"\n=== {r['case_key']} — {s['name']} ===")
    print(f"  generated by {llm.get('model') or '?'} ({llm.get('auth_method') or '?'}), "
          f"{s['chars']} chars, iteration {s['iterations']}, lint_ok={s['lint_ok']}")
    print(f"  inputs: {i['sequence_steps']} steps ({i['verify_steps']} verify), "
          f"{i['fragments_selected']}/{i['fragments_pool']} fragments selected, "
          f"fit={i['fit_decision']}")
    for cav in r.get("caveats", []):
        print(f"  ⚠ {cav}")
    print(f"  C1 template used   : {c['1_template_used']['verdict'].upper()}"
          f"  ({c['1_template_used']['testcase_classes']} TestCases / "
          f"{c['1_template_used']['verify_steps']} verify steps)")
    for f in c["1_template_used"]["findings"]:
        print(f"       - {f}")
    c2 = c["2_snippets_used"]
    print(f"  C2 snippets used   : {c2['verdict'].upper()}"
          + (f"  (tags {c2['tags_matched']}" if c2.get("tags_matched") else f"  ({c2.get('reason','')}")
          + (f", avg code overlap {c2['avg_code_overlap']})" if c2.get("avg_code_overlap") is not None else ")"))
    dups = [p["testcase"] for p in c2.get("per_step", []) if p.get("duplicate_tag_lines", 0) > 1]
    if dups:
        print(f"       - duplicate tag lines in main(): {', '.join(dups)}")
    c3 = c["3_snippet_order"]
    print(f"  C3 snippet order   : {c3['verdict'].upper()}"
          + (f"  ({c3.get('reason')})" if c3.get("reason") else ""))
    if c3["verdict"] == "wrong":
        print(f"       expected {c3['expected']}")
        print(f"       actual   {c3['actual']}")
    c6 = c["6_logging_contract_offline"]
    print(f"  C6 logging (offline): {c6['verdict'].upper()}  ({c6['conformant']} conformant)")
    for row in c6["per_testcase"]:
        if not row["ok"]:
            print(f"       - {row['testcase']}: {'; '.join(row['why'])}")
    print("  C4/C5/C6-hardware  : see 'blocked' (LLM judges / tb470)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Part 3a mechanical grader (criteria 1-3, 6-offline)")
    ap.add_argument("case_keys", nargs="*", help="AWPTCM-Txxxxx (default: all pt sessions)")
    ap.add_argument("--json", action="store_true", help="emit JSON to stdout")
    ap.add_argument("--out", metavar="DIR", help="also write <case>/mechanical.json under DIR")
    args = ap.parse_args()

    if not DB.exists():
        print(f"ck.db not found at {DB}", file=sys.stderr)
        return 2
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    keys = args.case_keys or all_case_keys(conn)
    reports = [grade_case(conn, k) for k in keys]

    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        print(f"PyTest Creator — Part 3a mechanical report ({len(reports)} case(s))")
        for r in reports:
            print_report(r)
        print()

    if args.out:
        for r in reports:
            if r.get("error"):
                continue
            d = Path(args.out) / r["case_key"]
            d.mkdir(parents=True, exist_ok=True)
            (d / "mechanical.json").write_text(json.dumps(r, indent=2))
        print(f"wrote mechanical.json for "
              f"{sum(1 for r in reports if not r.get('error'))} case(s) under {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
