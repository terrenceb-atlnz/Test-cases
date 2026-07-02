#!/usr/bin/env python3
"""Upload refined-cases/*/zephyr_payload.json + traceability.md + web links to Zephyr Scale (AWPTCM project).

Replaces / enriches objective + testScript on existing AWPTCM-Txxxx manual test cases
and attaches the corresponding traceability.md via the attachments API.

Also adds web links (from "ATPyLib Cases" and "Zephyr Cross-References (Step 3)" sections
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

Never modifies files on disk.
"""

import argparse
import glob
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from common import JIRA_BASE, SSL_CTX, need


def load_payload(path):
    """Load a zephyr_payload.json.

    Supports both wrapped shape:
      {"AWPTCM-T12345": {"objective": "...", "testScript": {...}}}
    and direct inner shape (for flexibility).
    Returns (key, payload_dict) or (None, None) on failure.
    Tries a light sanitize for common authoring escapes (e.g. stray \') to be
    tolerant of pre-existing data issues without modifying files on disk.
    """
    raw = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        obj = json.loads(raw)
    except Exception:
        if raw:
            # Light sanitize for common bad escapes seen in refined payloads
            try:
                fixed = raw.replace("\\'", "'").replace("\\ ", " ")
                obj = json.loads(fixed)
            except Exception as e2:
                print(f"ERROR reading {path}: {e2}", file=sys.stderr)
                return None, None
        else:
            print(f"ERROR reading {path}", file=sys.stderr)
            return None, None

    if isinstance(obj, dict):
        # Wrapped shape: top-level single AWPTCM- key
        if len(obj) == 1:
            k = next(iter(obj))
            if isinstance(k, str) and k.startswith("AWPTCM-"):
                inner = obj[k]
                if isinstance(inner, dict):
                    return k, inner
        # Direct shape or unexpected: scan for AWPTCM- key
        for k, v in obj.items():
            if isinstance(k, str) and k.startswith("AWPTCM-") and isinstance(v, dict):
                return k, v
        # Fallback: if file name encodes the key
        base = os.path.basename(os.path.dirname(path))
        if base.startswith("AWPTCM-"):
            return base, obj

    print(f"WARNING: could not extract AWPTCM key from {path}", file=sys.stderr)
    return None, None


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


def parse_atpylib_links(md_path):
    """Parse the ATPyLib Cases section of traceability.md and return list of {url, description} for web links."""
    import re
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
    # Find backticked IDs e.g. `1342.301.13` or `1346.*`
    for match in re.finditer(r'`(\d{4}(?:\.\d+)*|\d{4}\.\*)`', section):
        id_str = match.group(1)
        suite_id = id_str[:4]
        url = f"http://intranet.atlnz.lc/systest/ATPyLib/regression/test_suite.php?testSuiteId={suite_id}"
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
    """Parse the Zephyr Cross-References (Step 3) section and return tracelink entries for the referenced Zephyr cases.

    Looks for AWPTCM-Txxxx keys (preferably inside markdown links) and produces
    web links back into Zephyr Scale using the standard Tests.jspa deep link.
    """
    import re
    if not os.path.isfile(md_path):
        return []
    try:
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []

    m = re.search(r'## Zephyr Cross-References \(Step 3\)\s*(.*?)(?=\n## |\Z)', content, re.DOTALL | re.IGNORECASE)
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
    """Get the internal numeric testCaseId using the internal tests API."""
    q = urllib.parse.quote(f'testCase.key = "{key}"')
    url = f"{JIRA_BASE}/rest/tests/1.0/testcase/search?archived=false&fields=id,key&maxResults=1&query={q}"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    data = json.load(urllib.request.urlopen(req, context=SSL_CTX, timeout=30))
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


def put_case(key, objective=None, test_script=None, token=None, dry_run=True):
    """PUT fields to the test case (objective + testScript).

    Returns (success: bool, status_or_error)
    """
    url = f"{JIRA_BASE}/rest/atm/1.0/testcase/{key}"
    body = {}
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


def attach_file(key, filepath, token, dry_run=True):
    """Upload a file (e.g. traceability.md) as an attachment to the test case.

    Uses the /testcase/{key}/attachments endpoint.
    Returns (success: bool, status_or_error)
    """
    url = f"{JIRA_BASE}/rest/atm/1.0/testcase/{key}/attachments"
    filename = os.path.basename(filepath)

    if dry_run:
        print(f"  [DRY] Would POST attachment {filename} -> {url}", file=sys.stderr)
        return True, "dry-run"

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
    ap.add_argument("--limit", type=int, default=0, help="Process at most N cases (0 = no limit)")
    ap.add_argument("--continue-on-error", action="store_true", default=True,
                    help="Keep going after individual failures (default: on)")
    ap.add_argument("--only-weblinks", action="store_true",
                    help="Only POST web links via /rest/tests/1.0/tracelink/bulk/create (skip payload and attachment). Use with --force to override refined status.")
    ap.add_argument("--no-attach", action="store_true",
                    help="Skip attaching the traceability.md file to the test case")
    args = ap.parse_args()

    dry_run = not args.execute or args.dry_run

    # Discover payloads (run from project root or tool/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(script_dir)  # copilot/Test-cases
    base = os.path.join(root, "refined-cases")
    pattern = os.path.join(base, "**", "zephyr_payload.json")
    paths = sorted(glob.glob(pattern, recursive=True))

    if not paths:
        print("No zephyr_payload.json files found under refined-cases/", file=sys.stderr)
        sys.exit(1)

    # Filter
    selected = []
    for p in paths:
        try:
            key, payload = load_payload(p)
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
        selected.append((p, key, payload, rel_group))

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

    for i, (p, key, payload, group) in enumerate(selected, 1):
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

        # Skip logic only applies to payload updates. For --only-weblinks we always proceed with links.
        if do_payload and status == "refined" and not args.force:
            print("  SKIP: already appears refined in Zephyr (first step has ART note or substantial content).", file=sys.stderr)
            print("        Use --force to overwrite.", file=sys.stderr)
            already_present += 1
            skipped += 1
            continue

        if dry_run:
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

        # Real execute path
        ok = True
        if do_payload:
            ok, info = put_case(key, obj, ts, token, dry_run=False)
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
                if not do_payload:
                    successes += 1
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

    print(f"\nSummary: {successes} ok, {failures} failed, {skipped} skipped, {already_present} already-present", file=sys.stderr)
    if dry_run:
        print("Re-run with --execute to apply changes.", file=sys.stderr)
    elif already_present > 0 and not args.force:
        print("Tip: some cases were skipped because they already had refined content.", file=sys.stderr)

    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
