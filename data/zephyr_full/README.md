# Zephyr Full Database — Extracted Artifacts

**Source of truth (immutable)**: `Zephyr-Database-30_Jun_2026.xml` (120 MB XML export)  
**Extracted on**: 2026-06-30  
**Total cases**: 45427 (across many projects/folders, not limited to AWPTCM MASTER)

**Do not re-parse or load the raw XML for normal work.** Use the generated artifacts below.

## Best files for regular access (Step 3 cross-references)

| File                        | Size | Purpose                                                                 | Load strategy          |
|-----------------------------|------|-------------------------------------------------------------------------|------------------------|
| `slim_index.json`           | ~11MB| Tiny metadata for fast filtering (key, title, folder, labels, has_objective, num_steps) | Load fully into RAM (recommended) |
| `zephyr_cases.jsonl`        | 54MB | Full normalized case data, one JSON object per line (same shape as zephyr_master items) | Stream line-by-line   |
| `index.json` (legacy)       | 18MB | Heavier version with previews — prefer slim_index                       | —                      |

## Fast patterns you should use

**1. Filter using the slim index (fast, in-memory)**
```python
import json
idx = json.load(open("data/zephyr_full/slim_index.json"))

# Example: cases with "auto" in title or folder that have real objectives
matches = [c for c in idx
           if c.get("has_objective")
           and ("auto" in (c.get("title","") + " " + c.get("folder","")).lower())]
for m in matches[:8]:
    print(m["key"], m["num_steps"], m["title"][:60])
```

**2. Retrieve full details for specific keys (stream JSONL)**
```python
def get_full_case(key):
    with open("data/zephyr_full/zephyr_cases.jsonl") as f:
        for line in f:
            if f'"{key}"' in line[:40]:   # cheap early check
                return json.loads(line)
    return None

case = get_full_case("AWPTCM-T24")
print(case["objective"][:400] if case else "not found")
print("Steps:", len(case["steps"]) if case else 0)
```

**3. Ad-hoc shell searches**
```sh
# Titles containing certain phrases
grep -o '"title":"[^"]*auto[^"]*"' data/zephyr_full/zephyr_cases.jsonl | head -10

# Find cases that mention "link partner" or similar
grep -i "link partner" data/zephyr_full/zephyr_cases.jsonl | head -3
```

## Re-generate (if a newer export arrives)

```sh
python3 tool/extract_zephyr_xml.py \
    --xml /path/to/new-zephyr-export.xml \
    --out-dir data/zephyr_full \
    --force
```

The script uses streaming `xml.etree.ElementTree.iterparse` so it stays memory-efficient even on the full 120 MB file.

## Data model (normalized)
Each record matches the shape used by `data/zephyr_master.json`:
- key, title, folder, objective (cleaned text), precondition
- priority, status, labels[]
- script_type ("STEP_BY_STEP" | ...), steps: [{description, testData, expected}], script_text

`src` is set to `"zephyr_xml"`.

## Durability
- Original XML = archive / source of truth (never modify).
- These generated files = the durable, queryable working copy for the project.
- Re-running the extractor on the same XML produces equivalent output.

This format enables the efficient "intelligent cross-reference" required by Step 3 of the drafting process.
