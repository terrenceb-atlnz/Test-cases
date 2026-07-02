#!/usr/bin/env python3
"""Generate a starter draft stub for an AWPTCM manual test case.

Part of refining the Objective drafting process.

Usage:
  python3 tool/draft_stub.py AWPTCM-T33235

Outputs:
  - Suggested high-level objective (template form)
  - 5-7 step skeleton (generic)
  - Primary decision match + rationale
  - Recommended search keywords for test_id_description.json
  - Ready-to-edit JSON fragment for zephyr_api_updates.json

Helps keep Objectives consistent when moving beyond the initial Port family.
"""

import sys
import json
import glob
import re
import os

if len(sys.argv) < 2:
    print("Usage: python3 tool/draft_stub.py AWPTCM-Txxxx")
    sys.exit(1)

KEY = sys.argv[1]

# Resolve data dir relative to this script (allows running from tool/ or project root)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)  # copilot/Test-cases
DATA = os.path.join(ROOT, "data")

def load(p):
    return json.load(open(os.path.join(DATA, p)))

# Load data
cands = load("candidates.json")
zm = {c["key"]: c for c in load("zephyr_master.json")}

# Find primary decision
primary = None
why = ""
dec_glob = os.path.join(DATA, "decisions", "dec_*.json")
for f in sorted(glob.glob(dec_glob)):
    d = json.load(open(f))
    if KEY in d:
        primary = d[KEY].get("m")
        why = d[KEY].get("w", "")
        break

# Find candidate record
rec = next((c for c in cands if c["key"] == KEY), None)
if not rec:
    print(f"ERROR: {KEY} not found in candidates.json")
    sys.exit(1)

title = rec["title"]
area = rec.get("area", "")
feature = rec.get("feature", "")

# Pull a couple top candidate titles for keyword ideas
top_cand_titles = [c["title"] for c in rec.get("candidates", [])[:3]]

# Build suggested keywords
base_kw = []
for t in [title, feature] + top_cand_titles:
    for w in re.findall(r"[A-Za-z0-9]{3,}", t or ""):
        w = w.lower()
        if w not in base_kw and len(w) > 3:
            base_kw.append(w)
base_kw = base_kw[:8]

print("=" * 70)
print(f"OBJECTIVE DRAFT STUB for {KEY}")
print("=" * 70)
print(f"Title   : {title}")
print(f"Area    : {area} / {feature}")
print(f"Folder  : {rec['folder']}")
print(f"Primary decision match: {primary or 'None'}  ({why})")
print()

print("--- Suggested objective (artefact bullets - edit and expand into <ul><li> form) ---")
print("Produce declarative end-state statements (one per <li>), e.g.:")
print("- A port with no pluggable present defaults to ...")
print("- The port accurately reports ...")
print("- Link establishment succeeds when ...")
print("Wrap as: <ul><li>...</li>...</ul>  (number of bullets varies)")
print()

print("--- Recommended verification steps skeleton (number varies, adapt language) ---")
steps = [
    "Verify default / initial behavior and basic positive case.",
    "Configure the specific setting under test and confirm expected state + reporting.",
    "Vary configurations / partners / inputs across supported values.",
    "Test incompatible, error, or unsupported cases.",
    "Exercise special conditions (hot-swap, restart, scale, no-media, etc. where applicable).",
    "Verify reporting, show commands, logs, or side effects match expected state.",
    "Optional: persistence across save/reload or failover if relevant to the case."
]
for i, s in enumerate(steps, 1):
    print(f'{i}. {s}')
print()

print("--- Search seeds for test_id_description.json / suite_index ---")
print("python3 -c '")
print('import json')
print('data = json.load(open("data/suites/test_id_description.json"))')
print(f'kws = {base_kw}')
print('for tid, entry in data.items():')
print('    d = (entry.get("description") or "").lower()')
print('    if any(k in d for k in kws):')
print('        print(tid, ":", entry.get("description","")[:100])')
print("' | head -15")
print()

print("--- Partial JSON fragment for data/zephyr_api_updates.json (copy/edit) ---")
print("Note: objective must be the full '<ul><li>artefact1</li><li>artefact2</li>...</ul>' string.")
stub = {
    KEY: {
        "objective": "<ul><li>A [subject] [desired artefact/outcome].</li><li>The [component] accurately reports ...</li></ul>",
        "testScript": {
            "type": "steps",
            "steps": [
                {"description": s, "expectedResult": ""} for s in steps[:5]
            ]
        }
    }
}
print(json.dumps(stub, indent=2))
print()
print("Remember: after editing, run validation and cross-reference decisions.")
print("=" * 70)
