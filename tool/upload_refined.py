#!/usr/bin/env python3
"""Upload refined-cases/*/zephyr_payload.json + traceability.md + web links to Zephyr Scale (AWPTCM project).

Replaces / enriches objective + testScript on existing AWPTCM-Txxxx manual test cases
and attaches the corresponding traceability.md via the attachments API.

Also adds web links (from the "ATPyLib Cases" and "Zephyr Cross-References" sections
in traceability.md) via POST /rest/tests/1.0/tracelink/bulk/create (for Zephyr's "Web Links").

Use --only-weblinks to only do the web links part.
The refined-cases layout is the current source of truth (see OBJECTIVE_DRAFTING_PROCESS.md).

Auth: JIRA_KEY from environment variable, or automatically loaded from secrets.md
(next to this script or in current directory) as Bearer (same as extract_* tools).

Usage examples:
  # Safe preview (no network writes). Will auto-load JIRA_KEY from secrets.md if present.
  python3 tool/upload_refined.py --dry-run --keys AWPTCM-T33235

  # With explicit env var (takes precedence over secrets.md)
  JIRA_KEY=... python3 tool/upload_refined.py --dry-run --keys AWPTCM-T33235 AWPTCM-T33323

  # Actual upload of selected cases + post-verify GET
  JIRA_KEY=... python3 tool/upload_refined.py --execute --keys AWPTCM-T33235 --verify

  # Group-based (directory names under refined-cases)
  JIRA_KEY=... python3 tool/upload_refined.py --execute --groups "Port (7)" "QoS (22)" --verify

  # Force overwrite of a case that is already marked refined
  JIRA_KEY=... python3 tool/upload_refined.py --execute --keys AWPTCM-T33235 --force

  # Everything (use with care)
  JIRA_KEY=... python3 tool/upload_refined.py --execute --all --limit 5

Safety: --dry-run is the default mode. Real changes require --execute.
The script automatically loads JIRA_KEY from secrets.md (if present) when the
environment variable is not set. It performs pre-flight checks and will skip
cases that already appear to have refined content in Zephyr (based on
substantial objective + steps or the "Note: Related ART Tests" marker).
Use --force to overwrite.

Every payload is validated before it can reach a live case: the shape rules come
from the server (CK_server/llm.py:validate_zephyr_payload — imported, not restated),
plus the rule that every verification step must carry an expectedResult. An invalid
payload is refused; --skip-validation overrides. Validation runs in --dry-run too, so
the preview reports what would be refused. Every --execute writes an audit record to
ask-ck/var/zephyr-push-audit.jsonl before the first network write, and a case whose
audit record cannot be written is refused.

Never modifies files on disk.
"""

import argparse
import datetime
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from common import JIRA_BASE, JIRA_PROJECT_ID, SSL_CTX, need


def load_payload(path):
    """Load a zephyr_payload.json.

    Supports both wrapped shape:
      {"AWPTCM-T12345": {"objective": "...", "testScript": {...}}}
    and direct inner shape (for flexibility).
    Returns (key, payload_dict, repairs) or (None, None, repairs) on failure.

    `repairs` is a list of human-readable strings describing any escape-repair that
    was needed to parse the file. It used to be silent: a malformed bundle was
    patched in memory and pushed with no warning, so the operator could not tell a
    clean payload from a guessed one. The repair still happens (it is tolerant of
    pre-existing authoring damage and never modifies files on disk) but it is now
    reported, and main() refuses to --execute a repaired payload without an
    explicit override.
    """
    raw = None
    repairs = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        obj = json.loads(raw)
    except Exception as e1:
        if raw:
            # Light sanitize for common bad escapes seen in refined payloads
            try:
                fixed = raw.replace("\\'", "'").replace("\\ ", " ")
                obj = json.loads(fixed)
                repairs.append(
                    f"escape-repair applied to parse the file (\\' and '\\ '): the raw JSON "
                    f"is invalid — {e1}"
                )
            except Exception as e2:
                print(f"ERROR reading {path}: {e2}", file=sys.stderr)
                return None, None, repairs
        else:
            print(f"ERROR reading {path}", file=sys.stderr)
            return None, None, repairs

    if isinstance(obj, dict):
        # Wrapped shape: top-level single AWPTCM- key
        if len(obj) == 1:
            k = next(iter(obj))
            if isinstance(k, str) and k.startswith("AWPTCM-"):
                inner = obj[k]
                if isinstance(inner, dict):
                    return k, inner, repairs
        # Direct shape or unexpected: scan for AWPTCM- key
        for k, v in obj.items():
            if isinstance(k, str) and k.startswith("AWPTCM-") and isinstance(v, dict):
                return k, v, repairs
        # Fallback: if file name encodes the key
        base = os.path.basename(os.path.dirname(path))
        if base.startswith("AWPTCM-"):
            return base, obj, repairs

    print(f"WARNING: could not extract AWPTCM key from {path}", file=sys.stderr)
    return None, None, repairs


# --- validation before a live write -------------------------------------------
#
# The push used to send whatever JSON happened to be on disk: upload_refined.py never
# imported a validator of any kind. The shape rules are owned by the server
# (CK_server/llm.py:validate_zephyr_payload), so import them rather than restating
# them here — a second copy would drift, and the drift would only show up as bad data
# in a live Zephyr case.
#
# The import is lazy and FAILS CLOSED: if the server module cannot be loaded we treat
# that as a refusal under --execute, never as a pass.

_CK_SERVER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "ask-ck", "CK-main", "CK_server",
)

# The server-injected first step. Kept as a literal here (rather than imported)
# because the blank-expectedResult rule below must still work when the server import
# fails — that is exactly the case where we most need to know what we are pushing.
# CK_server/llm.py:846 is the owner; tests/test_zephyr_push_validation.py pins the two
# spellings against each other.
_NOTE_PREFIX = "Note: Related ART Tests linked in Traceability"


def _server_validator():
    """Return CK_server's validate_zephyr_payload, or None if it cannot be imported."""
    if _CK_SERVER_DIR not in sys.path:
        sys.path.insert(0, _CK_SERVER_DIR)
    try:
        from llm import validate_zephyr_payload  # CK_server import (cf. tool/pt_judge.py)
        return validate_zephyr_payload
    except Exception as e:                              # pragma: no cover - env-specific
        print(f"  WARNING: could not import the server validator: {e}", file=sys.stderr)
        return None


# THE BLANK-expectedResult RULE IS DELETED, NOT DISABLED.
#
# It used to refuse any push whose verification steps had no expectedResult ("a step with
# no expected result is not a test"), and it refused all 53 committed bundles. The premise
# was wrong. A Zephyr manual step is MEANT to leave the field empty — Terrence's design
# ruling, recorded in memory `expected-results-deliberately-absent`: a tester reading the
# objective plus a non-prescriptive step reasons out what should happen, and stating it
# narrows them to reproducing that exact result instead of producing evidence of function.
#
# The rule's own history is why this is a deletion rather than a flag. Phase −1 (`949004f`)
# asserted the premise here; hours later D-12 (`f0a94af`) rewrote `generate_steps.jinja` to
# satisfy it, justified by THIS gate refusing the corpus. Circular. Leaving the function
# behind, even unused, invites the same loop — so it goes, and `llm.synthesize_steps` now
# forces the field empty at generation.


def validate_for_push(key, payload):
    """Validate a payload before it is allowed to reach a live Zephyr case.

    Returns {"valid": bool, "issues": [...], "warnings": [...], "checked": bool}.
    `checked` is False when the server shape validator could not be run; callers must
    treat that as a refusal under --execute, not as a pass.
    """
    issues = []
    warnings = []
    checked = False

    validator = _server_validator()
    if validator is not None:
        try:
            res = validator({key: payload}) or {}
            issues.extend(res.get("issues") or [])
            warnings.extend(res.get("warnings") or [])
            checked = True
        except Exception as e:                          # pragma: no cover - defensive
            warnings.append(f"server validator raised: {e}")

    return {"valid": not issues, "issues": issues, "warnings": warnings, "checked": checked}


# --- audit log -----------------------------------------------------------------
#
# A real push mutates data outside this repository, in a system this project does not
# own, and until now it left no record at all: nothing said which case was written,
# by whom, when, or what it looked like beforehand. The log lives under ask-ck/var/,
# which .gitignore excludes (:79) — deliberately, since it records production writes
# and can quote case content.

AUDIT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "ask-ck", "var", "zephyr-push-audit.jsonl",
)


def audit(event, key, **fields):
    """Append one audit record. Returns True on success.

    Callers on the --execute path must treat False as a refusal: an unlogged
    production write is exactly the thing this log exists to prevent.
    """
    rec = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "event": event,
        "key": key,
        "user": os.environ.get("USER") or os.environ.get("LOGNAME") or "?",
        "pid": os.getpid(),
        "argv": sys.argv[1:],
    }
    rec.update(fields)
    try:
        os.makedirs(os.path.dirname(AUDIT_PATH), exist_ok=True)
        with open(AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        print(f"  AUDIT LOG WRITE FAILED ({AUDIT_PATH}): {e}", file=sys.stderr)
        return False


def normalize_test_script(ts):
    """Normalize authoring 'steps' to API 'STEP_BY_STEP'."""
    if not isinstance(ts, dict):
        return {"type": "STEP_BY_STEP", "steps": []}
    ts = dict(ts)  # shallow copy
    if ts.get("type") in ("steps", "STEP_BY_STEP"):
        ts["type"] = "STEP_BY_STEP"
    if "steps" not in ts:
        ts["steps"] = []
    return ts


def clean_test_script_for_update(ts):
    """Strip internal ids etc for PUT update."""
    if not ts:
        return {"type": "STEP_BY_STEP", "steps": []}
    steps = ts.get("steps") or []
    clean_steps = [{"description": s.get("description", ""), "expectedResult": s.get("expectedResult", "")} for s in steps]
    return {"type": ts.get("type", "STEP_BY_STEP"), "steps": clean_steps}


# A single leading parenthesised group at the very start of the title, e.g.
# "(4) Auto MDI/MDI-X" or "(draft) Foo" -> the "(…) " prefix. Numeric-or-not per
# Terrence's call (2026-07-22). Only the FIRST leading group is stripped; any
# parentheses later in the title are left untouched.
_LEADING_PAREN_RE = re.compile(r"^\s*\([^)]*\)\s*")


def strip_leading_paren_group(name):
    """Return (new_name, changed) with a single leading '(…)' group removed.

    "(4) Auto MDI/MDI-X" -> ("Auto MDI/MDI-X", True)
    "Auto MDI/MDI-X"     -> ("Auto MDI/MDI-X", False)
    A title that is *only* a parenthesised group (e.g. "(4)") is left unchanged
    rather than emptied, since Name is a required Zephyr field.
    """
    if not name:
        return name, False
    stripped = _LEADING_PAREN_RE.sub("", name, count=1)
    if stripped and stripped != name:
        return stripped, True
    return name, False


# ART suite/test IDs in the ATPyLib Cases section: 4-digit suite, optionally
# dotted (1342.301.13) or wildcard (1346.*). Not preceded by a word char / dot /
# hyphen so we don't pick up AWP-4341 TestLink numbers or fragments of longer ids.
_ATP_ID_RX = re.compile(r"(?<![\w.-])(\d{4}(?:\.\d+)*|\d{4}\.\*)\b")
# Bare 4-digit years seen in prose ("... in 2026 ...") are not suites.
_YEAR_RX = re.compile(r"^(?:19|20)\d\d$")
# 4-digit tokens that appear in prose but are NOT ART suites (reviewed 2026-07-22).
# Extend as more false-positives are found.
_NON_SUITE_IDS = {"1024"}


def parse_atpylib_links(md_path):
    """Parse the ATPyLib Cases section of traceability.md → list of {url, description}.

    Reads ART suite IDs from the '## ATPyLib Cases (Step 3|4)' section. IDs may be
    backticked (`1342.301.13`) OR bare prose ('1351 suite covers ...') — both are
    accepted, since most cases author them without backticks. Bare 4-digit years
    (19xx/20xx) and a small reviewed non-suite denylist are skipped. Links are
    per-suite (testSuiteId = first 4 digits) and de-duplicated by URL.
    """
    if not os.path.isfile(md_path):
        return []
    try:
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []

    # Extract the section (support old "Step 3" and current "Step 4")
    m = re.search(r'## ATPyLib Cases \(Step (?:3|4)\)\s*(.*?)(?=\n## |\Z)', content, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    section = m.group(1)

    links = []
    seen = set()
    for match in _ATP_ID_RX.finditer(section):
        id_str = match.group(1)
        suite_id = id_str.split(".")[0]
        if "." not in id_str and _YEAR_RX.match(id_str):
            continue  # bare year, not a suite
        if suite_id in _NON_SUITE_IDS:
            continue  # reviewed non-suite false-positive
        url = f"http://intranet.atlnz.lc/systest/ATPyLib/regression/test_suite.php?testSuiteId={suite_id}"
        if url in seen:
            continue  # one link per suite
        seen.add(url)
        if "." in id_str and not id_str.endswith("*"):
            parts = id_str.split(".")
            if len(parts) >= 3:
                desc = f"ART Suite {parts[0]} - Test {parts[1]}.{parts[2]}"
            else:
                desc = f"ART Suite {suite_id}"
        else:
            desc = f"ART Suite {suite_id}"
        links.append({"url": url, "description": desc})
    return links


def parse_zephyr_links(md_path):
    """Parse the Zephyr Cross-References section and return tracelink entries for the referenced Zephyr cases.

    Looks for AWPTCM-Txxxx keys (preferably inside markdown links) and produces
    web links back into Zephyr Scale using the standard Tests.jspa deep link.

    The step number in the heading is NOT stable. The traceability template emits
    "(Step 2)" (templates/outputs/traceability.md.jinja:23) while this parser looked
    only for "(Step 3)" — so the regex never matched, _zephyr_links came back empty,
    and step 4 of the advertised push silently did nothing on 12 of the 13 bundles
    that have cross-references. parse_atpylib_links already accepted "(Step 3|4)" for
    exactly this drift; the fix was never carried across. Accept either number, and
    let tests/test_zephyr_push_validation.py hold the template and the parser
    together so the next renumber is caught here rather than in production.
    """
    import re
    if not os.path.isfile(md_path):
        return []
    try:
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []

    m = re.search(r'## Zephyr Cross-References \(Step (?:2|3)\)\s*(.*?)(?=\n## |\Z)', content, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    section = m.group(1)

    links = []
    seen = set()

    # Prefer keys inside markdown links: [AWPTCM-T1234](https://.../AWPTCM-T1234)
    for match in re.finditer(r'\[([A-Z]+-T\d+)\]\(([^)]+)\)', section):
        key = match.group(1)
        url = match.group(2)
        if key in seen:
            continue
        seen.add(key)
        desc = f"Zephyr: {key}"
        links.append({"url": url, "description": desc})

    # Fallback: any AWPTCM-Txxxx key mentioned in the section (if no markdown link was present)
    if not links:
        for match in re.finditer(r'(AWPTCM-T\d+)', section):
            key = match.group(1)
            if key in seen:
                continue
            seen.add(key)
            url = f"https://jira.atlnz.lc/secure/Tests.jspa#/testCase/{key}"
            links.append({"url": url, "description": f"Zephyr: {key}"})

    return links


def get_test_case_numeric_id(key, token):
    """Get the internal numeric testCaseId (latest version) using the internal tests API.

    Returns the numeric id, or None on any error (bad token, not found, network),
    so callers can report cleanly instead of crashing.
    """
    q = urllib.parse.quote(f'testCase.key = "{key}"')
    url = f"{JIRA_BASE}/rest/tests/1.0/testcase/search?archived=false&fields=id,key&maxResults=1&query={q}"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        data = json.load(urllib.request.urlopen(req, context=SSL_CTX, timeout=30))
    except Exception as e:
        print(f"  WARN: could not resolve numeric id for {key}: {e}", file=sys.stderr)
        return None
    if data.get("results"):
        return data["results"][0]["id"]
    return None


def get_existing_tracelink_urls(key, token):
    """Fetch existing trace link URLs for a test case to avoid duplicates on re-runs."""
    q = urllib.parse.quote(f'testCase.key = "{key}"')
    url = f"{JIRA_BASE}/rest/tests/1.0/testcase/search?fields=id,key,traceLinks&maxResults=1&query={q}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "jira-project-id": "15310",
        },
    )
    try:
        data = json.load(urllib.request.urlopen(req, context=SSL_CTX, timeout=30))
        if data.get("results"):
            tl = data["results"][0].get("traceLinks") or []
            return {l.get("url") for l in tl if l.get("url")}
    except Exception:
        pass
    return set()


def post_tracelinks(key, links, token):
    """Add web links (as tracelinks) using the endpoint reverse-engineered from browser devtools.

    POST /rest/tests/1.0/tracelink/bulk/create
    Payload: [{"testCaseId": <num>, "url": "...", "urlDescription": "...", "typeId": 1}, ...]
    Uses Bearer PAT (works for this endpoint). Matches UI "Web Links" in Traceability.
    Skips links whose URL already exists for the test case.

    `links` can come from ATPyLib or Zephyr Cross-References sections.
    """
    if not links:
        return True, "no-op"
    tc_id = get_test_case_numeric_id(key, token)
    if not tc_id:
        return False, "could not resolve numeric testCaseId"
    existing = get_existing_tracelink_urls(key, token)
    payload = []
    for l in links:
        if l["url"] in existing:
            continue
        desc = l.get("description") or l.get("title")
        payload.append({
            "testCaseId": tc_id,
            "url": l["url"],
            "urlDescription": desc,
            "typeId": 1
        })
    if not payload:
        return True, "already present"
    url = f"{JIRA_BASE}/rest/tests/1.0/tracelink/bulk/create"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "jira-project-id": "15310",
        "X-Requested-With": "XMLHttpRequest",
    }
    try:
        req = urllib.request.Request(url, data=data, method="POST", headers=headers)
        resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=30)
        status = getattr(resp, "status", 200)
        try:
            body = json.load(resp)
        except Exception:
            body = resp.read().decode("utf-8", errors="replace")[:300]
        return True, (status, body)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)



def fetch_case(key, token):
    """Safely fetch current state of a test case. Returns dict or None on error."""
    if not token:
        return None
    try:
        return gj(f"/rest/atm/1.0/testcase/{key}", token)
    except Exception as e:
        print(f"  WARN: could not fetch current state for {key}: {e}", file=sys.stderr)
        return None


def get_refinement_status(current):
    """Heuristic: has this case already been enriched with a refined objective+script?

    Returns one of: "empty", "partial", "refined", "unknown"
    """
    if not current:
        return "unknown"

    obj = (current.get("objective") or "").strip()
    ts = current.get("testScript") or {}
    steps = ts.get("steps") or []

    # Strong marker used by the refined-cases workflow
    first_desc = (steps[0].get("description") or "") if steps else ""
    has_art_note = "Related ART Tests linked in Traceability" in first_desc

    obj_len = len(obj)
    step_count = len(steps)

    if has_art_note or (obj_len > 200 and step_count >= 3):
        return "refined"
    if obj_len > 30 or step_count > 1:
        return "partial"
    if obj_len > 0 or step_count > 0:
        return "partial"
    return "empty"


def gj(path, token):
    """GET helper (Bearer + SSL_CTX) modeled on extract_zephyr.py."""
    url = JIRA_BASE + path
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=60)
        return json.load(resp)
    except urllib.error.HTTPError as e:
        # Surface the body for 4xx/5xx
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:400]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code} for {path}: {body}") from e


def put_case(key, objective=None, test_script=None, name=None, token=None, dry_run=True):
    """PUT fields to the test case (name + objective + testScript).

    Only the fields passed as non-None are included in the body, so this can be
    used to update the title alone (name=...) or the payload alone.
    Returns (success: bool, status_or_error)
    """
    url = f"{JIRA_BASE}/rest/atm/1.0/testcase/{key}"
    body = {}
    if name is not None:
        body["name"] = name
    if objective is not None:
        body["objective"] = objective or ""
    if test_script is not None:
        body["testScript"] = test_script or {"type": "STEP_BY_STEP", "steps": []}

    data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if dry_run:
        print(f"  [DRY] PUT {url}", file=sys.stderr)
        if "name" in body:
            print(f"  name={body['name']!r}", file=sys.stderr)
        if "objective" in body:
            print(f"  objective len={len(body.get('objective', ''))}", file=sys.stderr)
        if "testScript" in body:
            print(f"  steps={len(body.get('testScript', {}).get('steps', []))}", file=sys.stderr)
        return True, "dry-run"

    if not body:
        return True, "no-op"

    try:
        req = urllib.request.Request(url, data=data, method="PUT", headers=headers)
        resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=60)
        # Zephyr often returns 200/204 with little/no body on success
        status = getattr(resp, "status", 200)
        return True, status
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def fix_title(key, token, dry_run=True, current=None):
    """Strip a leading '(…)' group from the case Name in Zephyr, if present.

    GETs the current name (unless `current` is supplied), strips a single leading
    parenthesised group, and PUTs the cleaned name only when it changed.
    Returns (status, old_name, new_name) where status is one of:
      "changed"   — name had a leading group; PUT issued (or dry-run previewed)
      "unchanged" — no leading group; nothing sent
      "no-name"   — could not read a current name
      "error:..." — GET/PUT failed
    """
    if current is None:
        current = fetch_case(key, token)
    if not current:
        return "no-name", None, None
    old_name = (current.get("name") or "").strip()
    if not old_name:
        return "no-name", None, None
    new_name, changed = strip_leading_paren_group(old_name)
    if not changed:
        return "unchanged", old_name, old_name
    if dry_run:
        print(f"  [DRY] would fix title: {old_name!r} -> {new_name!r}", file=sys.stderr)
        return "changed", old_name, new_name
    ok, info = put_case(key, name=new_name, token=token, dry_run=False)
    if ok:
        return "changed", old_name, new_name
    return f"error:{info}", old_name, new_name


# This process only ever takes a case to version 2.0 — never higher. See
# create_new_version(): bump 1.0 -> 2.0, but if the case is already at 2.0 (or
# beyond) do NOT create another version, so re-running never produces 3.0+.
TARGET_MAJOR_VERSION = 2


def get_case_version_info(key, token):
    """Return {id, majorVersion, latestVersion, name} for the case's latest version.

    Uses the internal tests API, which resolves a key to its latest version.
    Returns None on any error / no result.
    """
    q = urllib.parse.quote(f'testCase.key = "{key}"')
    url = (f"{JIRA_BASE}/rest/tests/1.0/testcase/search"
           f"?archived=false&fields=id,key,name,majorVersion,latestVersion&maxResults=1&query={q}")
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
    try:
        data = json.load(urllib.request.urlopen(req, context=SSL_CTX, timeout=30))
    except Exception as e:
        print(f"  WARN: could not read version info for {key}: {e}", file=sys.stderr)
        return None
    results = data.get("results") if isinstance(data, dict) else None
    if not results:
        return None
    return results[0]


def create_new_version(key, token, dry_run=True):
    """Ensure the case is at version 2.0, creating it from 1.0 if needed.

    On this Jira Server / Adaptavist ATM instance, the UI "New Version" button
    (its Accept confirmation) clones the case into a new latest version via:

        POST /rest/tests/1.0/testcase/{numericId}/newversion
        body: {"id": <numericId>}
        -> 201 {"key": "AWPTCM-Txxxx", "id": <newVersionNumericId>}

    The numeric id changes but the key is stable and the new version becomes the
    latest, so a subsequent atm/1.0 PUT *by key* lands objective/testScript on it.
    Callers run: fix_title -> create_new_version -> put_case(objective, testScript).

    IDEMPOTENT TOWARD 2.0 (per Terrence): this process only ever produces v2.0.
      - currently v1  -> create a new version (becomes v2.0)
      - already v2    -> do nothing (payload writes onto the existing v2.0)
      - already v3+   -> do nothing + warn (can't downgrade; anomaly to flag)

    Auth: Bearer PAT (same base as post_tracelinks). Returns (success, info) where
    info is a dict describing what happened (action: created|skipped|dry-run).
    """
    info = get_case_version_info(key, token)
    if not info:
        return False, "could not resolve case/version info"
    tc_id = info.get("id")
    major = info.get("majorVersion")
    if tc_id is None or major is None:
        return False, f"missing id/majorVersion for {key}"

    # Already at (or past) the target — never bump further.
    if major >= TARGET_MAJOR_VERSION:
        if major > TARGET_MAJOR_VERSION:
            print(f"  WARN: {key} is already at v{major}.0 (> target v{TARGET_MAJOR_VERSION}.0); "
                  f"not creating another version.", file=sys.stderr)
        else:
            print(f"  Already at v{major}.0 — no new version needed.", file=sys.stderr)
        return True, {"action": "skipped", "id": tc_id, "major": major}

    # major < target (i.e. v1) -> create a new version -> becomes v2.0
    if dry_run:
        print(f"  [DRY] would create v{major + 1}.0 via POST "
              f"/rest/tests/1.0/testcase/{tc_id}/newversion  body={{\"id\": {tc_id}}}", file=sys.stderr)
        return True, {"action": "dry-run", "id": tc_id, "target_major": major + 1}

    url = f"{JIRA_BASE}/rest/tests/1.0/testcase/{tc_id}/newversion"
    payload = {"id": tc_id}
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "jira-project-id": str(JIRA_PROJECT_ID),
        "X-Requested-With": "XMLHttpRequest",
    }
    try:
        req = urllib.request.Request(url, data=data, method="POST", headers=headers)
        resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=30)
        status = getattr(resp, "status", 201)
        new_id = None
        try:
            body = json.load(resp)
            if isinstance(body, dict):
                new_id = body.get("id")
        except Exception:
            pass
        print(f"  Created v{major + 1}.0 (status {status}, new id {new_id})", file=sys.stderr)
        return True, {"action": "created", "status": status, "new_id": new_id, "from_major": major}
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def get_attachments(key, token):
    """List attachments for a test case. Returns a list of dicts (id, filename, …) or []."""
    url = f"{JIRA_BASE}/rest/atm/1.0/testcase/{key}/attachments"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
    try:
        data = json.load(urllib.request.urlopen(req, context=SSL_CTX, timeout=30))
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  WARN: could not list attachments for {key}: {e}", file=sys.stderr)
        return []


def delete_attachment(att_id, token):
    """Delete an attachment by numeric id. Returns (ok, status_or_error)."""
    url = f"{JIRA_BASE}/rest/atm/1.0/attachments/{att_id}"
    req = urllib.request.Request(url, method="DELETE",
                                 headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
    try:
        resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=30)
        return True, getattr(resp, "status", 200)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def attach_file(key, filepath, token, dry_run=True):
    """Upload a file (e.g. traceability.md) as an attachment to the test case.

    REPLACE semantics: the attachments API has no update, and repeated pushes would
    otherwise accumulate duplicate copies (it does not dedupe). So any existing
    attachment with the SAME filename is deleted first, leaving exactly one, always
    the current one. Uses the /testcase/{key}/attachments endpoint.
    Returns (success: bool, status_or_error)
    """
    url = f"{JIRA_BASE}/rest/atm/1.0/testcase/{key}/attachments"
    filename = os.path.basename(filepath)

    existing_same = [a for a in get_attachments(key, token)
                     if isinstance(a, dict) and a.get("filename") == filename and a.get("id") is not None]

    if dry_run:
        if existing_same:
            print(f"  [DRY] would replace {len(existing_same)} existing '{filename}' "
                  f"attachment(s), then upload 1", file=sys.stderr)
        else:
            print(f"  [DRY] Would POST attachment {filename} -> {url}", file=sys.stderr)
        return True, "dry-run"

    # Remove existing same-named attachments so exactly one (fresh) copy remains.
    for a in existing_same:
        d_ok, d_info = delete_attachment(a["id"], token)
        if d_ok:
            print(f"  Removed old {filename} (id {a['id']})", file=sys.stderr)
        else:
            print(f"  WARN: could not remove old {filename} id {a['id']}: {d_info}", file=sys.stderr)

    try:
        import mimetypes
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        ctype = mimetypes.guess_type(filename)[0] or "text/markdown"

        with open(filepath, "rb") as f:
            file_content = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n"
        ).encode("utf-8") + file_content + f"\r\n--{boundary}--\r\n".encode("utf-8")

        headers = {
            "Authorization": "Bearer " + token,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        }

        req = urllib.request.Request(url, data=body, method="POST", headers=headers)
        resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=60)
        status = getattr(resp, "status", 200)
        return True, status
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


def get_relative_group(path):
    """Return first path component under refined-cases/ for grouping."""
    # e.g. refined-cases/Port (7)/AWPTCM-.../zephyr... -> "Port (7)"
    parts = os.path.normpath(path).split(os.sep)
    try:
        idx = parts.index("refined-cases")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    except ValueError:
        pass
    return "(root)"


def _find_secrets_file():
    """Search for secrets.md in a few sensible locations."""
    here = os.path.dirname(os.path.abspath(__file__))          # .../tool
    project_root = os.path.dirname(here)                       # .../copilot/Test-cases

    candidates = [
        os.path.join(project_root, "secrets.md"),              # preferred: next to refined-cases/
        os.path.abspath("secrets.md"),                         # cwd
        os.path.join(here, "secrets.md"),                      # inside tool/ (unlikely)
        os.path.join(project_root, "..", "secrets.md"),
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            return os.path.abspath(cand)
    return None


def get_jira_key():
    """Return JIRA_KEY.

    Priority:
      1. Environment variable JIRA_KEY (if set and non-empty)
      2. JIRA_KEY= line inside a secrets.md file
    """
    env_key = os.environ.get("JIRA_KEY", "").strip()
    if env_key:
        return env_key

    secrets_path = _find_secrets_file()
    if secrets_path:
        try:
            with open(secrets_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("JIRA_KEY="):
                        val = line.split("=", 1)[1].strip()
                        if val:
                            print(f"  (loaded JIRA_KEY from {secrets_path})", file=sys.stderr)
                            return val
        except Exception as e:
            print(f"  Warning: failed to read {secrets_path}: {e}", file=sys.stderr)
    return None


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Upload refined-cases from the Test-cases project to Zephyr Scale.\n\n"
            "Reads zephyr_payload.json files (objective + testScript) under refined-cases/\n"
            "and pushes them to the matching AWPTCM-Txxxx manual test cases.\n\n"
            "Authentication:\n"
            "  • JIRA_KEY environment variable (highest priority)\n"
            "  • Automatically loaded from secrets.md (JIRA_KEY=... line)\n\n"
            "Safety:\n"
            "  • --dry-run is the default. No writes occur unless --execute is used.\n"
            "  • Performs pre-flight GETs (when a key is available) and skips cases\n"
            "    that already appear refined (based on the ART note or substantial content).\n"
            "    Use --force to override."
        ),
        epilog="""\
RECOMMENDED WORKFLOW
  1. cd copilot/Test-cases
  2. Always start with --dry-run (completely safe)
  3. Review the "current in Zephyr" status and proposed changes
  4. Only run with --execute when you are happy with the preview

EXAMPLES

  # Safe dry-run on one or more specific cases
  # (automatically loads JIRA_KEY from secrets.md if not in env)
  python3 tool/upload_refined.py --dry-run --keys AWPTCM-T33235

  # Multiple keys
  python3 tool/upload_refined.py --dry-run --keys AWPTCM-T33235 AWPTCM-T33323

  # By group (directory name under refined-cases/)
  python3 tool/upload_refined.py --dry-run --groups "Port (7)" --limit 5

  # See a sample of everything
  python3 tool/upload_refined.py --dry-run --all --limit 3

  # Real upload (updates objective+script + attaches traceability.md)
  JIRA_KEY=... python3 tool/upload_refined.py --execute --keys AWPTCM-T33235 --verify

  # Force re-upload even if the case already looks refined
  python3 tool/upload_refined.py --execute --keys AWPTCM-T33235 --force

  # Only push web links (skip payload and attach) - use this for investigation
  python3 tool/upload_refined.py --execute --only-weblinks --keys AWPTCM-T33235 --force

  # Update payload but skip attaching traceability.md
  python3 tool/upload_refined.py --execute --no-attach --keys AWPTCM-T33235 --force

  # Override secrets.md with explicit env var
  JIRA_KEY=your-token-here python3 tool/upload_refined.py --dry-run --keys AWPTCM-T33241

The script will upload the zephyr_payload.json (objective + test steps) and, on successful
execute, will also attach the matching traceability.md to the same test case via the
attachments API (unless --no-attach).

It will also parse the "## ATPyLib Cases (Step 3)" section of traceability.md and send
web links using POST /rest/tests/1.0/tracelink/bulk/create (exact browser endpoint for UI Web Links).
Payload shape: [{"testCaseId": <numeric>, "url": "...", "urlDescription": "ART Suite XXXX - Test YYY.ZZ", "typeId": 1}]
Use --only-weblinks --force to only push weblinks.

Link text uses the format "ART Suite XXXX - Test YYY.ZZ" for dotted IDs like 1342.301.13.

MORE INFO
  See README.md (Uploading Refined Cases section) and
  OBJECTIVE_DRAFTING_PROCESS.md for background and the full workflow.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    ap.add_argument("--keys", nargs="*", metavar="AWPTCM-Txxxx",
                    help="Specific case keys to upload (space separated)")
    ap.add_argument("--groups", nargs="*", metavar="GROUP",
                    help='Category dir names under refined-cases/ e.g. "Port (7)" "IPv4 (44)"')
    ap.add_argument("--all", action="store_true", help="Upload every discovered refined case")
    ap.add_argument("--execute", action="store_true",
                    help="Perform real PUTs (default is dry-run / preview only)")
    ap.add_argument("--dry-run", action="store_true", help="Force dry-run mode (default)")
    ap.add_argument("--verify", action="store_true",
                    help="After successful PUT, re-GET the case and print short summary")
    ap.add_argument("--force", action="store_true",
                    help="Force update even if the case already appears refined in Zephyr")
    ap.add_argument("--skip-validation", action="store_true",
                    help="Push even when the payload fails validation (shape rules from the "
                         "server, plus the rule that every verification step must carry an "
                         "expectedResult). Off by default: an invalid payload is refused.")
    ap.add_argument("--limit", type=int, default=0, help="Process at most N cases (0 = no limit)")
    ap.add_argument("--continue-on-error", action="store_true", default=True,
                    help="Keep going after individual failures (default: on)")
    ap.add_argument("--only-weblinks", action="store_true",
                    help="Only POST web links via /rest/tests/1.0/tracelink/bulk/create (skip payload and attachment). Use with --force to override refined status.")
    ap.add_argument("--no-attach", action="store_true",
                    help="Skip attaching the traceability.md file to the test case")
    ap.add_argument("--fix-title", action="store_true",
                    help="Before uploading, strip a leading '(N)'/'(...)' group from the "
                         "case Name in Zephyr, e.g. '(4) Auto MDI/MDI-X' -> 'Auto MDI/MDI-X'.")
    ap.add_argument("--new-version", action="store_true",
                    help="Ensure the case is at version 2.0 BEFORE uploading the payload, so "
                         "objective+testScript land on v2.0. Bumps 1.0 -> 2.0; if already at 2.0 "
                         "(or higher) it does NOT create another version (never produces 3.0+).")
    args = ap.parse_args()

    dry_run = not args.execute or args.dry_run

    # Discover payloads (run from project root or tool/).
    # Post-2026-07-13 restructure, refined-cases live under
    # ask-ck/objective-drafting/refined-cases/; fall back to the pre-restructure
    # root location for older checkouts.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(script_dir)  # copilot/Test-cases
    base = os.path.join(root, "ask-ck", "objective-drafting", "refined-cases")
    if not os.path.isdir(base):
        base = os.path.join(root, "refined-cases")  # pre-restructure fallback
    pattern = os.path.join(base, "**", "zephyr_payload.json")
    paths = sorted(glob.glob(pattern, recursive=True))

    if not paths:
        print("No zephyr_payload.json files found under refined-cases/", file=sys.stderr)
        sys.exit(1)

    # Filter
    selected = []
    for p in paths:
        try:
            key, payload, repairs = load_payload(p)
        except Exception as e:
            print(f"ERROR loading {p}: {e}", file=sys.stderr)
            continue
        if not key:
            continue
        rel_group = get_relative_group(p)
        if args.keys and key not in args.keys:
            continue
        if args.groups and not any(g in rel_group or g in p for g in args.groups):
            continue
        if not (args.keys or args.groups or args.all):
            # Require explicit selection unless --all
            continue
        selected.append((p, key, payload, rel_group, repairs))

    if args.limit > 0:
        selected = selected[: args.limit]

    if not selected:
        print("No cases selected after filtering. Use --keys, --groups or --all.", file=sys.stderr)
        sys.exit(2)

    print(f"Discovered {len(paths)} payload files. Selected: {len(selected)}", file=sys.stderr)

    # Obtain token if available. In dry-run we use it for pre-flight "already added" checks only.
    # In execute mode it is required.
    # Automatically falls back to secrets.md if JIRA_KEY is not in the environment.
    token = get_jira_key()
    if not dry_run and not token:
        token = need("JIRA_KEY")

    if dry_run:
        print("=== DRY RUN (no changes will be made) ===", file=sys.stderr)
    else:
        print("=== EXECUTE MODE (changes will be written to Zephyr) ===", file=sys.stderr)

    successes = 0
    failures = 0
    skipped = 0
    already_present = 0
    blocked = 0

    for i, (p, key, payload, group, repairs) in enumerate(selected, 1):
        obj = payload.get("objective", "") if isinstance(payload, dict) else ""
        ts_raw = payload.get("testScript") if isinstance(payload, dict) else None
        ts = normalize_test_script(ts_raw)

        md_path = os.path.join(os.path.dirname(p), "traceability.md")
        atp_links = parse_atpylib_links(md_path)
        zephyr_links = parse_zephyr_links(md_path)
        all_links = atp_links + zephyr_links

        print(f"[{i}/{len(selected)}] {key}  [{group}]  {os.path.relpath(p, root)}", file=sys.stderr)

        # Pre-flight: check what is currently in Zephyr (when we have a token)
        current = fetch_case(key, token)
        status = get_refinement_status(current)

        cur_obj_len = 0
        cur_steps = 0
        if current:
            cur_obj_len = len((current.get("objective") or "").strip())
            cur_steps = len(((current.get("testScript") or {}).get("steps") or []))

        print(f"  current in Zephyr: status={status} (objective~{cur_obj_len}, steps={cur_steps})", file=sys.stderr)

        do_payload = not args.only_weblinks
        do_weblinks = bool(all_links)
        do_attach = not args.no_attach and not args.only_weblinks

        # Validation gate. Only payload pushes are gated: --only-weblinks writes no
        # objective and no steps, so an unvalidated payload cannot reach Zephyr on
        # that path. Runs in dry-run too, so the preview reports what WOULD be
        # refused instead of quietly previewing a push that could never succeed.
        if do_payload:
            verdict = validate_for_push(key, payload)
            problems = list(verdict["issues"])
            if not verdict["checked"]:
                problems.insert(0, "the server shape validator could not be run "
                                   "(refusing rather than pushing unvalidated content)")
            if repairs:
                for r in repairs:
                    print(f"  REPAIRED ON LOAD: {r}", file=sys.stderr)
                problems.append(
                    "the payload on disk is not valid JSON and was repaired in memory to "
                    "be read — fix the file rather than pushing a guess"
                )
            for w in verdict["warnings"]:
                print(f"  validation warning: {w}", file=sys.stderr)

            if problems:
                print(f"  VALIDATION FAILED ({len(problems)}):", file=sys.stderr)
                for it in problems:
                    print(f"    - {it}", file=sys.stderr)
                if not args.skip_validation:
                    print("  %s: refusing this payload (--skip-validation overrides)"
                          % ("WOULD BLOCK" if dry_run else "BLOCKED"), file=sys.stderr)
                    blocked += 1
                    continue
                print("  --skip-validation given: pushing anyway", file=sys.stderr)
            else:
                print("  validation: OK", file=sys.stderr)

        # Skip logic only applies to payload updates. For --only-weblinks we always proceed with links.
        if do_payload and status == "refined" and not args.force:
            print("  SKIP: already appears refined in Zephyr (first step has ART note or substantial content).", file=sys.stderr)
            print("        Use --force to overwrite.", file=sys.stderr)
            already_present += 1
            skipped += 1
            continue

        if dry_run:
            if args.fix_title:
                t_status, old_name, new_name = fix_title(key, token, dry_run=True, current=current)
                if t_status == "changed":
                    print(f"  would fix title: {old_name!r} -> {new_name!r}", file=sys.stderr)
                elif t_status == "unchanged":
                    print(f"  title ok (no leading group): {old_name!r}", file=sys.stderr)
                else:
                    print(f"  title: {t_status} (could not read current name)", file=sys.stderr)
            if args.new_version:
                v_ok, v_info = create_new_version(key, token, dry_run=True)
                if not v_ok:
                    print(f"  new version: WOULD FAIL — {v_info}", file=sys.stderr)
            if do_payload:
                print(f"  proposed: objective len={len(obj)}, steps={len(ts.get('steps', []))}", file=sys.stderr)
                if status in ("refined", "partial"):
                    print("  (would update; use --force in real run to override)", file=sys.stderr)
            if do_attach and os.path.isfile(md_path):
                print(f"  would also attach: {os.path.basename(md_path)}", file=sys.stderr)
            if do_weblinks:
                for l in all_links:
                    desc = l.get("description") or l.get("title")
                    print(f"  would set webLink: {desc} -> {l['url']}", file=sys.stderr)

            successes += 1
            continue

        # Real execute path.
        # Order matters (Terrence's spec): strip the title first, then create the
        # new version, then upload the payload so objective+testScript land on the
        # new version.
        #
        # Log the intent BEFORE the first write, with the pre-push state, so the
        # record survives a crash mid-sequence — a case can be left title-fixed and
        # version-bumped but not uploaded, and that partial state needs to be
        # reconstructable. A log that cannot be written blocks the case.
        #
        # The record carries the FULL prior objective + testScript, not just their
        # sizes. Zephyr keeps NO version history of these pushes by design (Terrence,
        # 2026-08-03: the 43 live cases stay at v2.0 and are overwritten in place —
        # a working copy, not a version-controlled one). That decision is about
        # Zephyr; it is precisely WHY a local record is worth keeping, because a
        # re-push that writes a worse objective over a better one is otherwise
        # unrecoverable. A few hundred KB, gitignored, never read by the server.
        before = {"status": status, "objective_chars": cur_obj_len, "steps": cur_steps}
        if current:
            before["objective"] = current.get("objective")
            before["testScript"] = current.get("testScript")
            before["name"] = current.get("name")
        else:
            before["read_failed"] = True

        if not audit(
            "push.intent", key,
            group=group, path=os.path.relpath(p, root),
            force=bool(args.force), skip_validation=bool(args.skip_validation),
            before=before,
            proposed={"objective_chars": len(obj), "steps": len(ts.get("steps", [])),
                      "weblinks": len(all_links)},
            actions={"payload": do_payload, "attach": do_attach, "weblinks": do_weblinks,
                     "fix_title": bool(args.fix_title), "new_version": bool(args.new_version)},
        ):
            print("  BLOCKED: refusing to write to Zephyr without an audit record.",
                  file=sys.stderr)
            blocked += 1
            continue

        ok = True

        if ok and args.fix_title:
            t_status, old_name, new_name = fix_title(key, token, dry_run=False, current=current)
            if t_status == "changed":
                print(f"  Title fixed: {old_name!r} -> {new_name!r}", file=sys.stderr)
            elif t_status == "unchanged":
                print(f"  Title unchanged (no leading group): {old_name!r}", file=sys.stderr)
            elif t_status == "no-name":
                print("  Title: could not read current name (skipping fix)", file=sys.stderr)
            else:
                ok = False
                failures += 1
                print(f"  FAILED title fix: {t_status}", file=sys.stderr)
                if not args.continue_on_error:
                    break

        if ok and args.new_version:
            # create_new_version is idempotent toward v2.0 and logs what it did.
            v_ok, v_info = create_new_version(key, token, dry_run=False)
            # Record what it actually did rather than inferring it from the
            # does-this-look-refined heuristic. action == "skipped" means the case was
            # already at v2.0, so nothing was cloned and the payload below overwrites
            # that version in place.
            action = v_info.get("action") if isinstance(v_info, dict) else None
            audit("push.version", key, ok=bool(v_ok), info=v_info,
                  overwrites_in_place=(action == "skipped"))
            if not v_ok:
                ok = False
                failures += 1
                print(f"  FAILED new version: {v_info}", file=sys.stderr)
                if not args.continue_on_error:
                    break

        if ok and do_payload:
            ok, info = put_case(key, obj, ts, token=token, dry_run=False)
            if ok:
                print(f"  OK payload (status {info})", file=sys.stderr)
            else:
                failures += 1
                print(f"  FAILED payload: {info}", file=sys.stderr)
                if not args.continue_on_error:
                    break

        if ok and do_attach and os.path.isfile(md_path):
            a_ok, a_info = attach_file(key, md_path, token, dry_run=False)
            if a_ok:
                print(f"  Attached: {os.path.basename(md_path)} (status {a_info})", file=sys.stderr)
            else:
                print(f"  Attachment of traceability.md failed: {a_info}", file=sys.stderr)
                # continue anyway

        if ok and do_weblinks:
            ok2, info2 = post_tracelinks(key, all_links, token)
            if ok2:
                status = info2[0] if isinstance(info2, (list, tuple)) else info2
                print(f"  Set webLink(s) via tracelink/bulk/create: OK (status {status})", file=sys.stderr)
                for l in all_links:
                    desc = l.get("description") or l.get("title")
                    print(f"    {desc} -> {l['url']}", file=sys.stderr)
            else:
                print(f"  Set webLink(s) FAILED: {info2}", file=sys.stderr)
                if not args.continue_on_error:
                    ok = False

        if ok and args.verify:
            try:
                after = gj(f"/rest/atm/1.0/testcase/{key}", token)
                after_obj = after.get("objective", "") or ""
                after_ts = after.get("testScript") or {}
                after_steps = after_ts.get("steps") or []
                print(f"  VERIFY: objective~{len(after_obj)} chars, steps={len(after_steps)}", file=sys.stderr)
            except Exception as ve:
                print(f"  VERIFY failed: {ve}", file=sys.stderr)

        # Count one success per case that completed its requested actions cleanly.
        if ok:
            successes += 1
        audit("push.outcome", key, ok=bool(ok))

    print(f"\nSummary: {successes} ok, {failures} failed, {blocked} blocked by validation, "
          f"{skipped} skipped, {already_present} already-present", file=sys.stderr)
    if blocked:
        print(f"{blocked} case(s) did not reach Zephyr because the payload failed validation. "
              f"Fix the payload — or pass --skip-validation if you have decided to push it "
              f"anyway.", file=sys.stderr)
    if dry_run:
        print("Re-run with --execute to apply changes.", file=sys.stderr)
    elif already_present > 0 and not args.force:
        print("Tip: some cases were skipped because they already had refined content.", file=sys.stderr)

    # A blocked case is a non-zero exit: the server surfaces returncode as `ok`, and a
    # push that refused half its cases must not read as success in the UI.
    sys.exit(0 if (failures == 0 and blocked == 0) else 1)


if __name__ == "__main__":
    main()
