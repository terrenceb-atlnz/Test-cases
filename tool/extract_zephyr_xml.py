"""Extract the full Zephyr XML export into durable, query-efficient formats.

This is the recommended way to access the large inherited Zephyr database
(>2.3M lines, ~45k test cases) for regular intelligent cross-referencing
without ever loading or reparsing the full XML repeatedly.

Usage:
  python3 tool/extract_zephyr_xml.py \
      --xml Zephyr-Database-30_Jun_2026.xml \
      --out-dir data/zephyr_full

Outputs (in --out-dir):
  - zephyr_cases.jsonl     : newline-delimited normalized cases (durable, grep-able)
  - index.json             : lightweight metadata array for fast in-memory filtering
  - README.md              : provenance + how to re-run
  - (future) zephyr.db     : SQLite + FTS (optional enhancement)

The normalized records are intentionally compatible in shape with the
items in data/zephyr_master.json (from the live API extractor).

The original XML is treated as immutable source of truth and is never modified.
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
import re
import html as htmllib
from datetime import datetime

# Reuse the project's html cleaner when available
try:
    from common import html_to_text as common_html_to_text
except Exception:
    common_html_to_text = None


def html_to_text(s):
    if not s:
        return ""
    if common_html_to_text:
        return common_html_to_text(s)
    # Fallback (same logic as common.py)
    _TAG = re.compile(r"<[^>]+>")
    _WS = re.compile(r"[ \t\xa0]+")
    s = s.replace("&nbsp;", " ")
    s = _TAG.sub(" ", s)
    s = htmllib.unescape(s)
    s = _WS.sub(" ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    return s.strip()


def norm_script(ts_elem):
    """Normalize <testScript> element (matches shape from extract_zephyr.py)."""
    if ts_elem is None:
        return {"script_type": "NONE", "script_text": "", "steps": []}

    t = (ts_elem.get("type") or "").lower()
    if t in ("steps", "step_by_step"):
        steps = []
        for step in ts_elem.findall(".//step"):
            desc = html_to_text(step.findtext("description") or "")
            exp = html_to_text(step.findtext("expectedResult") or "")
            steps.append({
                "description": desc,
                "testData": "",
                "expected": exp
            })
        return {"script_type": "STEP_BY_STEP", "script_text": "", "steps": steps}

    # Plain / text script or other
    text = ""
    for txt in ts_elem.findall(".//text"):
        text = html_to_text("".join(txt.itertext()))
        if text:
            break
    return {
        "script_type": (ts_elem.get("type") or "PLAIN").upper(),
        "script_text": text,
        "steps": []
    }


def parse_testcase(elem):
    """Turn a <testCase> element into the normalized dict shape."""
    key = elem.get("key")
    name = (elem.findtext("name") or "").strip()
    folder = elem.findtext("folder") or ""
    # Some exports omit leading /; make consistent with API data when possible
    if folder and not folder.startswith("/"):
        folder = "/" + folder

    obj_el = elem.find("objective")
    obj = html_to_text("".join(obj_el.itertext())) if obj_el is not None else ""

    pre_el = elem.find("precondition")
    pre = html_to_text("".join(pre_el.itertext())) if pre_el is not None else ""

    prio = (elem.findtext("priority") or "").strip()
    stat = (elem.findtext("status") or "").strip()

    labels = []
    for lab in elem.findall(".//label"):
        txt = (lab.text or "").strip()
        if txt:
            labels.append(txt)

    ts_el = elem.find("testScript")
    script = norm_script(ts_el)

    rec = {
        "src": "zephyr_xml",
        "key": key,
        "title": name,
        "folder": folder,
        "objective": obj,
        "precondition": pre,
        "priority": prio,
        "status": stat,
        "labels": labels,
    }
    rec.update(script)
    return rec


def build_index_record(rec):
    """Minimal record for fast filtering / overview."""
    obj = rec.get("objective", "") or ""
    steps = rec.get("steps") or []
    return {
        "key": rec.get("key"),
        "title": rec.get("title", ""),
        "folder": rec.get("folder", ""),
        "labels": rec.get("labels", []),
        "status": rec.get("status", ""),
        "priority": rec.get("priority", ""),
        "has_objective": bool(obj.strip()),
        "num_steps": len(steps),
        "objective_preview": (obj[:160] + "…") if len(obj) > 160 else obj,
    }


def main():
    parser = argparse.ArgumentParser(description="Stream-extract full Zephyr XML export")
    parser.add_argument("--xml", default="Zephyr-Database-30_Jun_2026.xml",
                        help="Path to the large Zephyr XML export")
    parser.add_argument("--out-dir", default="data/zephyr_full",
                        help="Directory for generated durable artifacts")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing output files")
    args = parser.parse_args()

    xml_path = args.xml
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    jsonl_path = os.path.join(out_dir, "zephyr_cases.jsonl")
    index_path = os.path.join(out_dir, "index.json")
    readme_path = os.path.join(out_dir, "README.md")

    if (os.path.exists(jsonl_path) or os.path.exists(index_path)) and not args.force:
        print(f"ERROR: Output already exists in {out_dir}. Use --force to overwrite.", file=sys.stderr)
        sys.exit(1)

    print(f"Streaming parse of {xml_path} ...", file=sys.stderr)

    count = 0
    index = []
    with open(jsonl_path, "w", encoding="utf-8") as jf:
        for event, elem in ET.iterparse(xml_path, events=("end",)):
            if elem.tag != "testCase":
                continue

            try:
                rec = parse_testcase(elem)
                # Write one line
                jf.write(json.dumps(rec, ensure_ascii=False) + "\n")

                # Build tiny index entry
                index.append(build_index_record(rec))
                count += 1

                if count % 5000 == 0:
                    print(f"  processed {count} cases...", file=sys.stderr)
            except Exception as e:
                print(f"Warning: failed to parse a testCase: {e}", file=sys.stderr)

            elem.clear()  # Critical: release memory for streaming

    # Write the full index (with previews)
    with open(index_path, "w", encoding="utf-8") as idx:
        json.dump(index, idx, ensure_ascii=False, indent=1)

    # Also write a slim, fast-load index (recommended for regular use)
    slim_path = os.path.join(out_dir, "slim_index.json")
    slim = []
    for c in index:
        slim.append({
            "key": c["key"],
            "title": c["title"],
            "folder": c["folder"],
            "labels": c["labels"],
            "status": c.get("status", ""),
            "has_objective": c["has_objective"],
            "num_steps": c["num_steps"]
        })
    with open(slim_path, "w", encoding="utf-8") as sidx:
        json.dump(slim, sidx, ensure_ascii=False)
    print(f"  {slim_path} (recommended for fast filtering)", file=sys.stderr)

    # Provenance README
    with open(readme_path, "w", encoding="utf-8") as rm:
        rm.write(f"""# Zephyr Full Database — Extracted Artifacts

**Source of truth (immutable)**: `{os.path.abspath(xml_path)}`  
**Extracted on**: {datetime.utcnow().isoformat()}Z  
**Total cases**: {count}

## Recommended access (for regular cross-reference use)

Do **not** re-parse the 120 MB XML for every query.

### Fast filter (load once)
```python
import json
idx = json.load(open("data/zephyr_full/index.json"))
matches = [c for c in idx
           if "auto" in (c["title"] or "").lower()
           and "port" in (c["folder"] or "").lower()]
print(len(matches))
for m in matches[:5]: print(m["key"], m["title"][:70])
```

### Full case details
Stream the JSONL (memory safe):
```python
def get_case(key):
    with open("data/zephyr_full/zephyr_cases.jsonl") as f:
        for line in f:
            d = json.loads(line)
            if d["key"] == key:
                return d
    return None
```

Or use shell for quick title/folder searches:
```sh
grep -i "auto.*negotiat" data/zephyr_full/zephyr_cases.jsonl | head -5
```

### Re-generate from a new export
```sh
python3 tool/extract_zephyr_xml.py --xml /path/to/new-export.xml --out-dir data/zephyr_full --force
```

## Files
- `zephyr_cases.jsonl` — Complete normalized data (one JSON object per line).
- `index.json` — Small metadata for fast filtering + previews.
- This README.

These files are the durable working copy for the Step 3 (Zephyr cross-reference) process.
Keep the original XML as archive.
""")

    print(f"\nWrote {count} cases", file=sys.stderr)
    print(f"  {jsonl_path}", file=sys.stderr)
    print(f"  {index_path}  ({len(index)} index entries)", file=sys.stderr)
    print(f"  {readme_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
