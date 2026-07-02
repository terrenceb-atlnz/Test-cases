"""Render candidates.json into compact markdown batches for in-session rerank.

Part of Test-cases project workflow: reviewing candidates from TestLink/AWP data against Manual Test Cases to capture matches and synthesize Objectives.

Usage: python3 render_batches.py [batch_size]  (default 30)
Writes data/review/batch_NN.md
"""
import sys, json, os, re

SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 30
TOPC = 8
C = json.load(open("data/candidates.json"))
os.makedirs("data/review", exist_ok=True)


def clip(s, n):
    return re.sub(r"\s+", " ", (s or "")).strip()[:n]


nb = (len(C) + SIZE - 1) // SIZE
for b in range(nb):
    rows = C[b * SIZE:(b + 1) * SIZE]
    lines = [f"# Rerank batch {b:02d}  (cases {b*SIZE}..{b*SIZE+len(rows)-1})", ""]
    for x in rows:
        fld = x["folder"].replace("/New Platform Test (MASTER)", "")
        lines.append(f"### {x['key']}  |  area: {x['area']}  |  feature: {x['feature']}")
        lines.append(f"folder:{fld}  steps:{x['n_steps']}  obj:{x['has_objective']}")
        if x.get("self_snippet"):
            lines.append(f"ZEPHYR: {clip(x['self_snippet'],200)}")
        for cd in x["candidates"][:TOPC]:
            lines.append(f"  - {cd['id']:11} {cd['score']:.3f} [{clip(cd['suite'],22):22}] "
                         f"{clip(cd['title'],55):55} :: {clip(cd['snippet'],130)}")
        lines.append("")
    open(f"data/review/batch_{b:02d}.md", "w").write("\n".join(lines))
print(f"wrote {nb} batches of {SIZE} -> data/review/")
