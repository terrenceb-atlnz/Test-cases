"""Extract all test cases in the AWPTCM "New Platform Test (MASTER)" folder to JSON.

The target Manual Test Cases for the Test-cases project (these lack Objectives; enriched data from TestLink + ATPyLib is used to synthesize them and map related Test Suites).

Usage (on terrenceb-dl):  JIRA_KEY=... python3 extract_zephyr.py [out.json]

Enumerates every subfolder path under MASTER (atm folder search is non-recursive),
searches each, then fetches the full case (incl. testScript) for each key.
"""
import sys, json, urllib.parse, urllib.request
from common import (JIRA_BASE, JIRA_PROJECT_KEY, JIRA_PROJECT_ID, MASTER_FOLDER,
                    SSL_CTX, need, html_to_text, dump)

OUT = sys.argv[1] if len(sys.argv) > 1 else "zephyr_master.json"
TOKEN = need("JIRA_KEY")


def gj(path):
    r = urllib.request.Request(JIRA_BASE + path,
                               headers={"Authorization": "Bearer " + TOKEN})
    return json.load(urllib.request.urlopen(r, context=SSL_CTX, timeout=60))


def all_master_paths():
    tree = gj(f"/rest/tests/1.0/project/{JIRA_PROJECT_ID}/foldertree/testcase")
    def find(n):
        for c in n.get("children", []):
            if c.get("name") == "New Platform Test (MASTER)":
                return c
            r = find(c)
            if r:
                return r
    m = find(tree)
    paths = [MASTER_FOLDER]  # include node itself (usually empty)
    def collect(n, prefix):
        for c in n.get("children", []):
            p = prefix + "/" + c["name"]
            paths.append(p)
            collect(c, p)
    collect(m, MASTER_FOLDER)
    return paths


def search_folder(path):
    q = urllib.parse.quote(f'projectKey = "{JIRA_PROJECT_KEY}" AND folder = "{path}"')
    return gj(f"/rest/atm/1.0/testcase/search?maxResults=1000&fields=key&query={q}")


def norm_script(ts):
    ts = ts or {}
    t = ts.get("type")
    if t == "STEP_BY_STEP":
        steps = [{"description": html_to_text(s.get("description")),
                  "testData": html_to_text(s.get("testData")),
                  "expected": html_to_text(s.get("expectedResult"))}
                 for s in (ts.get("steps") or [])]
        return {"script_type": t, "script_text": "", "steps": steps}
    return {"script_type": t or "NONE", "script_text": html_to_text(ts.get("text")),
            "steps": []}


def norm_case(full):
    n = {
        "src": "zephyr",
        "key": full.get("key"),
        "title": (full.get("name") or "").strip(),
        "folder": full.get("folder"),
        "objective": html_to_text(full.get("objective")),
        "precondition": html_to_text(full.get("precondition")),
        "priority": full.get("priority"),
        "status": full.get("status"),
        "labels": full.get("labels") or [],
    }
    n.update(norm_script(full.get("testScript")))
    return n


def main():
    paths = all_master_paths()
    print(f"{len(paths)} folder paths under MASTER", file=sys.stderr)
    keys = []
    for p in paths:
        hits = search_folder(p)
        keys += [h["key"] for h in hits]
        print(f"  {p[:60]:60} +{len(hits)}", file=sys.stderr)
    keys = sorted(set(keys))
    print(f"{len(keys)} unique cases; fetching full content...", file=sys.stderr)
    out = []
    for i, k in enumerate(keys, 1):
        out.append(norm_case(gj(f"/rest/atm/1.0/testcase/{k}")))
        if i % 50 == 0:
            print(f"  {i}/{len(keys)}", file=sys.stderr)
    dump(out, OUT)


if __name__ == "__main__":
    main()
