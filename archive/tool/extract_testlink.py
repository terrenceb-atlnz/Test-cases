"""Extract the full Alliedware Plus TestLink corpus to normalized JSON.

Supports the Test-cases project (historical TestLink data used alongside enriched ATPyLib Automated Suites to derive Objectives for AWPTCM Manual Test Cases and many-to-one mappings).

Usage (on terrenceb-dl):  TESTLINK_DEVKEY=... python3 extract_testlink.py [out.json]

Walks all first-level suites of the AWP project and pulls every test case with
summary, preconditions and steps via the efficient bulk call.
"""
import sys, xmlrpc.client
from common import TESTLINK_RPC, TESTLINK_PROJECT_ID, SSL_CTX, need, html_to_text, dump

OUT = sys.argv[1] if len(sys.argv) > 1 else "testlink_awp.json"
key = need("TESTLINK_DEVKEY")
s = xmlrpc.client.ServerProxy(TESTLINK_RPC, context=SSL_CTX, allow_none=True)


def norm_step(st):
    return {
        "n": st.get("step_number"),
        "action": html_to_text(st.get("actions")),
        "expected": html_to_text(st.get("expected_results")),
    }


def norm_case(c, top):
    steps = c.get("steps") or []
    if not isinstance(steps, list):
        steps = []
    return {
        "src": "testlink",
        "id": c.get("full_external_id") or c.get("external_id"),
        "internal_id": c.get("id"),
        "title": (c.get("name") or "").strip(),
        "suite_top": top,
        "suite": c.get("tsuite_name"),
        "summary": html_to_text(c.get("summary")),
        "preconditions": html_to_text(c.get("preconditions")),
        "steps": [norm_step(x) for x in steps],
        "importance": c.get("importance"),
        "status": c.get("status"),
    }


def main():
    tops = s.tl.getFirstLevelTestSuitesForTestProject(
        {"devKey": key, "testprojectid": TESTLINK_PROJECT_ID})
    out = []
    for i, t in enumerate(tops, 1):
        name = t.get("name")
        try:
            cases = s.tl.getTestCasesForTestSuite(
                {"devKey": key, "testsuiteid": t["id"], "deep": True, "details": "full"})
        except Exception as e:
            print(f"  ! suite {name} failed: {e}", file=sys.stderr)
            continue
        if not isinstance(cases, list):
            cases = []
        for c in cases:
            out.append(norm_case(c, name))
        print(f"  [{i}/{len(tops)}] {str(name)[:40]:40} +{len(cases)} (total {len(out)})",
              file=sys.stderr)
    dump(out, OUT)


if __name__ == "__main__":
    main()
