"""Validation's Finalize (ask-ck/plans/PLAN-test-validation.md §6) — built as far as V0 allows.

The four actions, in Terrence's order ("only remove the case after a successful upload"):
  1+4. the case leaves the PyTest Creator and the Objective / Test Case Creator lists — a
       `finalized_at` marker in generated/.meta/<group>/<name>/provenance.json, which
       case_registry.is_hidden_case honours (display-only, like the hidden-case list);
  2.   Zephyr: step 1 of the case gains, on the line after the templated "attachments" sentence,
       "This test is now automatable. use script <TITLE> in the ask-ck tool. <LINK>";
  3.   Zephyr: the case's version 2.0 → 3.0.
Zephyr goes FIRST (2 then 3, an audit line before each — the zephyr-tool pattern: stop and
report, no automatic undo); the marker is written only after both succeed.

V0 is open: the request Zephyr's UI sends to create a new version is not captured yet, so
`new_version` has no default and the endpoint refuses (409) with that reason. Nothing here writes
Zephyr until it is supplied.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

ADDENDUM = "This test is now automatable. use script {title} in the ask-ck tool. {link}"
V0_MISSING = ("Zephyr's \"create new version\" request has not been captured yet (PLAN-test-validation V0): "
              "capture it once with the browser's Network tab open, then Finalize can write.")


class FinalizeBlocked(RuntimeError):
    """Finalize cannot proceed; the message says why (shown to the user as-is)."""


def addendum(title: str, link: str) -> str:
    return ADDENDUM.format(title=title, link=link)


def step1_with_addendum(test_script: Dict[str, Any], text: str) -> Dict[str, Any]:
    """The testScript with `text` on the line after step 1's description. Idempotent."""
    ts = json.loads(json.dumps(test_script or {}))
    steps = ts.get("steps") or []
    if not steps:
        raise FinalizeBlocked("the case has no step 1 to add the note to")
    desc = steps[0].get("description") or ""
    if text in desc:
        return ts
    steps[0]["description"] = (desc.rstrip() + "<br />" if desc.strip() else "") + text
    ts["steps"] = steps
    return ts


def provenance_path(generated: Path, script_rel_to_generated: str) -> Path:
    p = Path(script_rel_to_generated)
    return generated / ".meta" / p.parent / p.stem / "provenance.json"


def mark_finalized(generated: Path, script_rel_to_generated: str, run_id: str, by: str) -> Dict[str, Any]:
    pp = provenance_path(generated, script_rel_to_generated)
    prov = json.loads(pp.read_text(encoding="utf-8")) if pp.is_file() else {}
    prov.update(finalized_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                finalized_run=run_id, finalized_by=by)
    pp.parent.mkdir(parents=True, exist_ok=True)
    pp.write_text(json.dumps(prov, indent=2), encoding="utf-8")
    return prov


def finalize(case_key: str, script_rel: str, run_id: str, by: str, generated: Path, link: str,
             get_case: Callable[[str], Dict[str, Any]], put_case: Callable[[str, Dict[str, Any]], None],
             new_version: Optional[Callable[[str], None]], audit: Callable[[Dict[str, Any]], bool]) -> Dict[str, Any]:
    """Run the four actions. Raises FinalizeBlocked before any write when something is missing."""
    if new_version is None:
        raise FinalizeBlocked(V0_MISSING)
    title = Path(script_rel).stem
    case = get_case(case_key)
    ts = step1_with_addendum(case.get("testScript") or {}, addendum(title, link))
    if not audit({"event": "finalize-step1", "case": case_key, "run": run_id, "by": by}):
        raise FinalizeBlocked("the audit log cannot be written — nothing was sent")
    put_case(case_key, ts)
    if not audit({"event": "finalize-version", "case": case_key, "run": run_id, "by": by}):
        raise FinalizeBlocked("the audit log cannot be written — step 1 was updated, the version was not")
    new_version(case_key)
    prov = mark_finalized(generated, script_rel, run_id, by)
    audit({"event": "finalized", "case": case_key, "run": run_id})
    return {"case": case_key, "finalized_at": prov["finalized_at"]}
