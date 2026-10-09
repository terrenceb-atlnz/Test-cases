"""Test Composer / Validation run records (ask-ck/plans/PLAN-agent-sessions.md §6, P1).

A run is one /test-mode campaign launched from Ask-CK. The SERVER owns the record; the SEAT owns
the session (D7: the page hands the hand-off to the seat agent, which runs the session under the
seat's own login, and relays its events back here). So everything below is files, never ck.db:

    <runs dir>/<YYYY-MM-DD>/<run_id>/handoff.json   the hand-off (schema 1) — written once
    <runs dir>/<YYYY-MM-DD>/<run_id>/run.json       the record: state, results, notices, cost
    <runs dir>/<YYYY-MM-DD>/<run_id>/events.jsonl   the session's events as the page relayed them

The runs dir is ask-ck/functions/test-composer/runs/ (CK_TC_RUNS_DIR overrides it; the specs use
tmp). Results are read ONLY from marker lines (`RESULT <id> <VERDICT> -- <reason> -- <log>`,
`NOTIFY <scope> -- <needed> -- <did instead>`, `ASKCK-DONE <run_id>`; logged-output.md §2,
test-mode §10) — never from prose. A leaf: imports paths only.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from paths import ASKCK_ROOT, PT_GENERATED_DIR, REFINED_DIR

REPO_ROOT = ASKCK_ROOT.parent
TC_ROOT = ASKCK_ROOT / "functions" / "test-composer"
TEMPLATES_DIR = TC_ROOT / "templates"
SCHEMA = 1
KINDS = ("validation", "composer", "composer-validate")
TERMINAL = ("done", "stopped", "error")

TESTBOX_RE = re.compile(r"^tb\d{1,4}$")
CASE_RE = re.compile(r"^AWPTCM-T\d+$")
RUN_ID_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{4}-[a-z]{3}-[a-z0-9]{4}$")
TEMPLATE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
# Free text the Test Engineer writes ("u0-u5 all (u0 = x230 DUT; u2,u4,u5 stack)"), carried as JSON to the
# session and never to a shell: only control characters are refused, and the length is capped.
CONSOLES_RE = re.compile(r"^[^\x00-\x1f\x7f]{1,300}$")
IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
VERDICTS = ("PASS", "FAIL", "PARTIAL", "UNSUPPORTED", "ERROR", "BLOCKED", "NOT TESTED", "SKIP")
_LOCK = threading.Lock()


class RunError(ValueError):
    """A request the page must correct (422)."""


def runs_dir() -> Path:
    return Path(os.environ.get("CK_TC_RUNS_DIR") or (TC_ROOT / "runs"))


def generated_dir() -> Path:
    return Path(os.environ.get("CK_PT_GENERATED_DIR") or PT_GENERATED_DIR)


def _now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def new_run_id(kind: str, now: Optional[datetime] = None) -> str:
    now = now or _now()
    return f"{now:%Y-%m-%dT%H%M}-{kind[:3]}-{secrets.token_hex(2)}"


def run_dir(run_id: str) -> Path:
    if not RUN_ID_RE.match(run_id or ""):
        raise RunError("malformed run id")
    return runs_dir() / run_id[:10] / run_id


# ------------------------------------------------------------------ scripts (Validation's picker)

def list_scripts() -> List[Dict[str, Any]]:
    """Saved scripts under generated/<group>/<name>.py with what provenance.json knows."""
    gen = generated_dir()
    out = []
    if not gen.is_dir():
        return out
    for py in sorted(gen.glob("*/*.py")):
        group, name = py.parent.name, py.stem
        if group.startswith(".") or name.startswith("library_"):
            continue
        meta = gen / ".meta" / group / name
        prov = {}
        try:
            prov = json.loads((meta / "provenance.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        out.append({"path": f"{group}/{py.name}", "group": group, "name": name,
                    "case_key": prov.get("case_key"), "family": prov.get("group"),
                    "saved_at": prov.get("saved_at"), "iterations": prov.get("iterations"),
                    "validated_at": prov.get("validated_at"), "finalized_at": prov.get("finalized_at")})
    return out


def script_abspath(rel: str) -> Path:
    """generated/<group>/<name>.py, refusing anything outside generated/."""
    gen = generated_dir().resolve()
    p = (gen / rel).resolve()
    if gen not in p.parents or p.suffix != ".py" or not p.is_file():
        raise RunError(f"no saved script {rel!r}")
    return p


# ------------------------------------------------------------------ templates

def list_templates() -> List[Dict[str, Any]]:
    out = []
    if TEMPLATES_DIR.is_dir():
        for d in sorted(p for p in TEMPLATES_DIR.iterdir() if p.is_dir()):
            setups = sorted(d.glob("*.setup"))
            setup = setups[0] if setups else None
            text = setup.read_text(encoding="utf-8") if setup else ""
            cases_txt = d / "cases.txt"
            manual = [ln.strip() for ln in cases_txt.read_text(encoding="utf-8").splitlines()
                      if CASE_RE.match(ln.strip())] if cases_txt.is_file() else []
            out.append({"name": d.name, "setup": setup.name if setup else None,
                        "setup_empty": not text.strip(), "configs": sorted(p.name for p in d.glob("*.cfg")),
                        "manual_cases": manual})
    return out


# ------------------------------------------------------------------ the hand-off

START_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def next_start(hhmm: str, now: datetime) -> datetime:
    """The next local `HH:MM` at or after `now` (today, else tomorrow) — after-hours runs (D3)."""
    m = START_RE.match(hhmm.strip())
    if not m:
        raise RunError("start time must be HH:MM (24-hour)")
    t = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
    return t if t >= now.replace(second=0, microsecond=0) else t + timedelta(days=1)


def build_handoff(body: Dict[str, Any], seat: str, now: Optional[datetime] = None) -> Dict[str, Any]:
    kind = body.get("kind")
    if kind not in KINDS:
        raise RunError(f"kind must be one of {KINDS}")
    testbox = str(body.get("testbox") or "").strip()
    if not TESTBOX_RE.match(testbox):
        raise RunError("testbox must look like tb470")
    consoles = str(body.get("consoles") or "").strip()
    if not CONSOLES_RE.match(consoles):
        raise RunError("say which consoles the session may use, e.g. u0-u5")
    pdu = body.get("pdu") or {}
    pdu_ip = str(pdu.get("ip") or "").strip()
    if pdu_ip and not IP_RE.match(pdu_ip):
        raise RunError("PDU IP is not an IPv4 address")
    outlets = {str(k): int(v) for k, v in (pdu.get("outlets") or {}).items()
               if re.match(r"^u\d{1,2}$", str(k)) and str(v).isdigit()}
    cases = []
    for c in body.get("cases") or []:
        key = str(c.get("key") or "").strip()
        if not CASE_RE.match(key):
            raise RunError(f"bad case key {key!r}")
        ck = c.get("kind") if c.get("kind") in ("script", "manual") else None
        if not ck:
            raise RunError(f"{key}: kind must be script or manual")
        entry = {"key": key, "kind": ck}
        if ck == "script":
            sp = script_abspath(str(c.get("script") or ""))
            entry["script"] = str(sp)
            # Repo-relative too: a seat or testbox mounts the lab home elsewhere, so device-testing
            # resolves this against the Test-cases checkout BESIDE its own (<dt root>/../Test-cases).
            entry["script_rel"] = _repo_rel(sp)
        if c.get("cycle"):
            entry["cycle"] = str(c["cycle"])[:40]
        # The refined case (objective + steps) the Validation review checks the script against
        # (PLAN-test-validation §5); repo-relative like the script.
        payload = next(iter(sorted(REFINED_DIR.glob(f"*/{key}/zephyr_payload.json"))), None) if REFINED_DIR.is_dir() else None
        entry["case_payload_rel"] = _repo_rel(payload) if payload else None
        cases.append(entry)
    if kind == "validation" and len([c for c in cases if c["kind"] == "script"]) != 1:
        raise RunError("a Validation run has exactly one script")
    if kind != "composer-validate" and not cases:
        raise RunError("no cases")
    template = body.get("template")
    template_setup_rel = None
    if template is not None:
        if not TEMPLATE_RE.match(str(template)) or not (TEMPLATES_DIR / str(template)).is_dir():
            raise RunError(f"no template {template!r}")
        setups = sorted((TEMPLATES_DIR / str(template)).glob("*.setup"))
        if not setups:
            raise RunError(f"template {template!r} has no .setup file")
        template_setup_rel = _repo_rel(setups[0])
    if kind == "composer-validate" and template is None:
        raise RunError("a composer-validate run needs a template")
    email = str((body.get("options") or {}).get("email") or "").strip()
    if email and not all(EMAIL_RE.match(e.strip()) for e in email.split(",")):
        raise RunError("email is not an address (comma-separate several)")
    start_after = (body.get("options") or {}).get("start_after") or None
    start_at = None
    if start_after:
        start_at = next_start(str(start_after), now or _now()).isoformat(timespec="seconds")
    run_id = new_run_id(kind, now)
    return {
        "schema": SCHEMA, "run_id": run_id, "kind": kind, "seat": seat,
        "created": (now or _now()).isoformat(timespec="seconds"),
        "testbox": testbox, "consoles": consoles,
        "pdu": {"ip": pdu_ip or None, "outlets": outlets} if pdu_ip else None,
        "constraints": str(body.get("constraints") or "").strip()[:1000],
        "template": template, "template_setup_rel": template_setup_rel, "project": body.get("project") if isinstance(body.get("project"), dict) else None,
        "cases": cases,
        "options": {"email": email or None, "start_after": start_after},
        "start_at": start_at,
    }


def _repo_rel(p: Path) -> Optional[str]:
    """Path relative to the Test-cases checkout, or None for a file outside it (the specs' tmp)."""
    try:
        return Path(p).resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return None


def create_run(body: Dict[str, Any], seat: str) -> Dict[str, Any]:
    handoff = build_handoff(body, seat)
    d = run_dir(handoff["run_id"])
    d.mkdir(parents=True, exist_ok=False)
    (d / "handoff.json").write_text(json.dumps(handoff, indent=2), encoding="utf-8")
    record = {"run_id": handoff["run_id"], "kind": handoff["kind"], "testbox": handoff["testbox"],
              "seat": seat, "created": handoff["created"],
              "state": "scheduled" if handoff["options"].get("start_after") else "created",
              "last_seq": -1, "results": {}, "notices": [], "regrades": {}, "cost_usd": None,
              "tokens": None, "turns": None, "started": None, "ended": None, "session_id": None,
              "cases": [{"key": c["key"], "kind": c["kind"], "cycle": c.get("cycle"),
                         "script": c.get("script")} for c in handoff["cases"]],
              "mailed": [], "start_at": handoff.get("start_at")}
    _write(d, record)
    return {"run_id": handoff["run_id"], "handoff": handoff, "record": record}


def _write(d: Path, record: Dict[str, Any]) -> None:
    tmp = d / "run.json.tmp"
    tmp.write_text(json.dumps(record, indent=2), encoding="utf-8")
    os.replace(tmp, d / "run.json")


def load(run_id: str) -> Dict[str, Any]:
    d = run_dir(run_id)
    try:
        return json.loads((d / "run.json").read_text(encoding="utf-8"))
    except OSError:
        raise KeyError(run_id) from None


def load_handoff(run_id: str) -> Dict[str, Any]:
    return json.loads((run_dir(run_id) / "handoff.json").read_text(encoding="utf-8"))


def list_runs(limit: int = 50, kind: Optional[str] = None) -> List[Dict[str, Any]]:
    root = runs_dir()
    out = []
    if not root.is_dir():
        return out
    for rj in sorted(root.glob("*/*/run.json"), reverse=True):
        try:
            r = json.loads(rj.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if kind and r.get("kind") != kind:
            continue
        out.append({k: r.get(k) for k in ("run_id", "kind", "testbox", "state", "created", "started", "ended",
                                          "cost_usd", "tokens")}
                   | {"counts": verdict_counts(r), "cases": [c["key"] for c in r.get("cases") or []]})
        if len(out) >= limit:
            break
    return out


# ------------------------------------------------------------------ events → the record

RESULT_RE = re.compile(r"^RESULT\s+(\S+)\s+(NOT TESTED|[A-Z]+)\s*(?:--\s*(.*?)\s*)?(?:--\s*(\S+)\s*)?$")
NOTIFY_RE = re.compile(r"^NOTIFY\s+(\S+)\s+--\s*(.*?)\s*--\s*(.*)$")


def parse_result(line: str) -> Optional[Dict[str, Any]]:
    m = RESULT_RE.match(line.strip())
    if not m:
        return None
    case = m.group(1)
    if re.match(r"^T\d+$", case):
        case = "AWPTCM-" + case
    elif re.match(r"^\d+$", case):
        case = "AWPTCM-T" + case
    return {"case": case, "verdict": m.group(2), "reason": (m.group(3) or "").strip(), "log": m.group(4)}


def parse_notify(line: str) -> Optional[Dict[str, Any]]:
    m = NOTIFY_RE.match(line.strip())
    return {"scope": m.group(1), "needed": m.group(2), "did": m.group(3)} if m else None


def verdict_counts(record: Dict[str, Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for case, r in (record.get("results") or {}).items():
        v = (record.get("regrades") or {}).get(case, {}).get("verdict") or r.get("verdict")
        counts[v] = counts.get(v, 0) + 1
    return counts


def table_counts(record: Dict[str, Any]) -> Dict[str, int]:
    """Counts as the results TABLE shows them: every case of the run, a case with no RESULT line
    counted NOT TESTED once the run has ended (the finish mail and the table must agree)."""
    counts: Dict[str, int] = {}
    for row in results_table(record):
        v = (row.get("regrade") or {}).get("verdict") or row["verdict"]
        counts[v] = counts.get(v, 0) + 1
    return counts


def _tokens(model_usage: Any) -> Optional[int]:
    if not isinstance(model_usage, dict):
        return None
    total = 0
    for u in model_usage.values():
        if isinstance(u, dict):
            total += sum(int(u.get(k) or 0) for k in ("inputTokens", "outputTokens",
                                                       "cacheReadInputTokens", "cacheCreationInputTokens"))
    return total


def apply_events(run_id: str, events: List[Dict[str, Any]], session_id: Optional[str] = None
                 ) -> Dict[str, Any]:
    """Append the page-relayed events (idempotent by seq) and fold them into run.json. Returns
    {record, new_notices, finished} so the router can mail about what changed."""
    d = run_dir(run_id)
    with _LOCK:
        record = load(run_id)
        fresh = sorted((e for e in events if isinstance(e, dict) and isinstance(e.get("seq"), int)
                        and e["seq"] > record.get("last_seq", -1)), key=lambda e: e["seq"])
        new_notices, was_terminal = [], record.get("state") in TERMINAL
        if session_id and not record.get("session_id"):
            record["session_id"] = session_id
        with open(d / "events.jsonl", "a", encoding="utf-8") as fh:
            for e in fresh:
                fh.write(json.dumps(e, default=str) + "\n")
                record["last_seq"] = e["seq"]
                k = e.get("kind")
                if k == "state":
                    st = e.get("state")
                    if st == "running" and not record.get("started"):
                        record["started"] = _now().isoformat(timespec="seconds")
                    if st in ("running",) + TERMINAL:
                        record["state"] = st
                    if st in TERMINAL:
                        record["ended"] = _now().isoformat(timespec="seconds")
                        if e.get("error"):
                            record["error"] = str(e["error"])[:500]
                elif k == "marker":
                    line = e.get("line") or ""
                    r = parse_result(line)
                    if r:
                        record["results"][r["case"]] = {"verdict": r["verdict"], "reason": r["reason"],
                                                         "log": r["log"], "seq": e["seq"]}
                    n = parse_notify(line)
                    if n and n not in record["notices"]:
                        record["notices"].append(n)
                        new_notices.append(n)
                    if line.startswith("ASKCK-DONE"):
                        record["done_marker"] = True
                elif k == "result":
                    if e.get("total_cost_usd") is not None:
                        record["cost_usd"] = e["total_cost_usd"]
                    t = _tokens(e.get("model_usage"))
                    if t is not None:
                        record["tokens"] = t
                    record["turns"] = e.get("num_turns")
        _write(d, record)
    return {"record": record, "new_notices": new_notices,
            "finished": record.get("state") in TERMINAL and not was_terminal}


def read_events(run_id: str, after: int = -1, limit: int = 2000) -> List[Dict[str, Any]]:
    p = run_dir(run_id) / "events.jsonl"
    out = []
    try:
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if e.get("seq", -1) > after:
                    out.append(e)
                    if len(out) >= limit:
                        break
    except OSError:
        pass
    return out


def regrade(run_id: str, case: str, verdict: str, note: str, by: str) -> Dict[str, Any]:
    """Terrence (the person at the page) is top of the grading tier list: a re-grade is recorded
    BESIDE the original verdict, never over it (memory grading-authority-tier-list)."""
    if verdict not in VERDICTS:
        raise RunError(f"verdict must be one of {VERDICTS}")
    with _LOCK:
        record = load(run_id)
        if case not in (record.get("results") or {}) and case not in [c["key"] for c in record.get("cases") or []]:
            raise RunError(f"{case} is not in this run")
        record.setdefault("regrades", {})[case] = {"verdict": verdict, "note": note[:1000], "by": by,
                                                     "at": _now().isoformat(timespec="seconds")}
        _write(run_dir(run_id), record)
    return record


def mark(run_id: str, **fields) -> Dict[str, Any]:
    with _LOCK:
        record = load(run_id)
        record.update(fields)
        _write(run_dir(run_id), record)
    return record


def results_table(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One row per case: cycle, script/manual, verdict (and any re-grade beside it), reason, log."""
    rows = []
    by_key = {c["key"]: c for c in record.get("cases") or []}
    keys = list(by_key) + [k for k in (record.get("results") or {}) if k not in by_key]
    for k in keys:
        c = by_key.get(k, {})
        r = (record.get("results") or {}).get(k)
        rows.append({"case": k, "kind": c.get("kind") or "?", "cycle": c.get("cycle"),
                     "verdict": r["verdict"] if r else ("PENDING" if record.get("state") not in TERMINAL else "NOT TESTED"),
                     "reason": r["reason"] if r else "", "log": r["log"] if r else None,
                     "regrade": (record.get("regrades") or {}).get(k)})
    return rows


# ------------------------------------------------------------------ after-hours runs (D3, P4)

def due_runs(seat: str, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Scheduled runs of THIS seat whose start time has come. The seat agent polls this; only the
    seat that created a run starts it (its own login runs the session — K1)."""
    now = now or _now()
    out = []
    root = runs_dir()
    if not root.is_dir():
        return out
    for rj in sorted(root.glob("*/*/run.json")):
        try:
            r = json.loads(rj.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if r.get("state") == "scheduled" and r.get("seat") == seat and r.get("start_at") \
                and datetime.fromisoformat(r["start_at"]) <= now:
            out.append({"run_id": r["run_id"], "start_at": r["start_at"], "kind": r["kind"]})
    return out


def claim(run_id: str, seat: str) -> Dict[str, Any]:
    """scheduled → claimed, once (the poller may race a second agent or a re-poll). Returns the
    hand-off for the agent to start; raises RunError when the run is not this seat's to start."""
    with _LOCK:
        r = load(run_id)
        if r.get("seat") != seat:
            raise RunError("this run belongs to another seat")
        if r.get("state") != "scheduled":
            raise RunError(f"run is {r.get('state')}, not scheduled")
        r.update(state="claimed", claimed_at=_now().isoformat(timespec="seconds"))
        _write(run_dir(run_id), r)
    return load_handoff(run_id)
