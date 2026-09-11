"""Build a lightweight self-contained HTML viewer for .json files under refined-cases/.

Provides:
- Dropdown selector of refined JSON files
- Two views:
    * Source (the zephyr_payload.json as authored)
    * After upload (Zephyr) - simulated shape returned by GET /rest/atm/1.0/testcase/{key}
      after the payload has been PUT. Useful for verifying objective HTML + step formatting.

Re-run whenever files are added to refined-cases/.

Usage:
    python3 tool/build_refined_viewer.py
    python3 tool/build_refined_viewer.py my-viewer.html
"""

import sys
import json
import glob
import os
from collections import defaultdict

OUT = sys.argv[1] if len(sys.argv) > 1 else "refined-viewer.html"
BASE = "refined-cases"

# Discover JSON files
paths = sorted(glob.glob(f"{BASE}/**/*.json", recursive=True))

# Load zephyr master so we can synthesize realistic "after upload" records
MASTER_PATH = os.path.join("data", "zephyr_master.json")
master = {}
if os.path.exists(MASTER_PATH):
    try:
        for c in json.load(open(MASTER_PATH, encoding="utf-8")):
            if c.get("key"):
                master[c["key"]] = c
    except Exception as e:
        print(f"Warning: could not load {MASTER_PATH}: {e}")

data = {}
groups = defaultdict(list)

for p in paths:
    try:
        with open(p, "r", encoding="utf-8") as f:
            obj = json.load(f)

        # Determine the AWPTCM key and the update payload content
        case_key = None
        payload_content = obj
        if isinstance(obj, dict) and len(obj) == 1:
            k = next(iter(obj))
            if isinstance(k, str) and k.startswith("AWPTCM-"):
                case_key = k
                payload_content = obj[k] if isinstance(obj[k], dict) else {}

        base = master.get(case_key, {}) if case_key else {}

        # Build a "Zephyr after upload" representation (what GET would return)
        zephyr_obj = {
            "key": case_key or "UNKNOWN",
            "name": base.get("title") or (case_key or ""),
            "folder": base.get("folder", ""),
            "objective": payload_content.get("objective", "") if isinstance(payload_content, dict) else "",
            "precondition": (payload_content.get("precondition") if isinstance(payload_content, dict) else None) or base.get("precondition", ""),
            "priority": base.get("priority", "Normal"),
            "status": base.get("status", "Draft"),
            "labels": base.get("labels", []),
            "testScript": (payload_content.get("testScript") if isinstance(payload_content, dict) else None) or {"type": "STEP_BY_STEP", "steps": []}
        }
        # Normalize testScript type to match live Zephyr API responses
        if isinstance(zephyr_obj.get("testScript"), dict):
            if zephyr_obj["testScript"].get("type") == "steps":
                zephyr_obj["testScript"]["type"] = "STEP_BY_STEP"

        data[p] = {
            "source": obj,
            "zephyr": zephyr_obj
        }

        # Group by first subdirectory
        parts = p.split(os.sep)
        cat = parts[1] if len(parts) > 2 else "(root)"
        groups[cat].append(p)
    except Exception as e:
        print(f"Warning: skipped {p}: {e}")

if not data:
    print("No JSON files found under refined-cases/")
    sys.exit(1)

DATA_JS = json.dumps(data, ensure_ascii=False)
# Build grouped <select> HTML on the Python side for cleanliness
select_html_parts = []
for cat in sorted(groups.keys()):
    select_html_parts.append(f'  <optgroup label="{cat}">')
    for p in groups[cat]:
        select_html_parts.append(f'    <option value="{p}">{p}</option>')
    select_html_parts.append("  </optgroup>")
SELECT_HTML = "\n".join(select_html_parts)

PAGE = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Refined Cases JSON Viewer</title>
<style>
:root {
  --bg:#0f1115; --card:#171a21; --mut:#8b95a7; --fg:#e7ecf3; --line:#262b36;
  --acc:#3b82f6; --prebg:#0d1017;
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
  font:14px/1.45 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }
header { position:sticky; top:0; z-index:10; background:#0f1115ee; backdrop-filter:blur(8px);
  border-bottom:1px solid var(--line); padding:14px 20px; }
h1 { font-size:17px; margin:0 0 6px; font-weight:600; }
h1 span { font-weight:400; color:var(--mut); font-size:12px; }
.controls { display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-top:8px; }
input, select, button {
  background:var(--card); color:var(--fg); border:1px solid var(--line);
  border-radius:6px; padding:7px 10px; font-size:13px; }
select { min-width: 420px; max-width: 680px; }
button { cursor:pointer; }
button.primary { background:var(--acc); border-color:var(--acc); color:#fff; font-weight:600; }
main { max-width: 1100px; margin: 0 auto; padding: 18px 20px; }
#meta { font-family: ui-monospace, monospace; font-size:12px; color:var(--mut); margin: 0 0 8px; }
#display {
  background: var(--prebg);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  min-height: 420px;
  max-height: 78vh;
  overflow: auto;
  white-space: pre;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  font-size: 12.5px;
  line-height: 1.5;
  color: #d1d9e3;
}
#display:empty::before {
  content: "Select a file from the dropdown above";
  color: var(--mut);
  font-style: italic;
}
.footer { margin-top:12px; font-size:11px; color:var(--mut); }
a { color:#7aa2f7; text-decoration:none; }
a:hover { text-decoration:underline; }
</style>
</head>
<body>
<header>
  <h1>Refined Cases &mdash; JSON Viewer <span>(source vs. after-upload to Zephyr)</span></h1>
  <div class="controls">
    <input id="filter" type="text" placeholder="filter files..." style="width:220px">
    <select id="sel">
__SELECT_OPTIONS__
    </select>
    <select id="view" title="Choose which representation to display">
      <option value="source">Source (zephyr_payload.json)</option>
      <option value="zephyr" selected>After upload (Zephyr format)</option>
    </select>
    <button id="copy" class="primary">Copy</button>
    <button id="download">Download .json</button>
    <button id="toggle">Minify</button>
  </div>
</header>

<main>
  <div id="meta"></div>
  <pre id="display"></pre>

  <div id="preview-controls" style="margin-top:14px; font-size:12px; color:#8b95a7; display:flex; align-items:center; gap:10px;">
    <span style="margin-right:4px;">Preview:</span>
    <label style="cursor:pointer; user-select:none;"><input type="radio" name="pview" value="objective" checked> Objective</label>
    <label style="cursor:pointer; user-select:none;"><input type="radio" name="pview" value="steps"> Test Steps</label>
  </div>
  <div id="preview" style="display:none; margin-top:6px;"></div>

  <div class="footer">
    Data embedded from refined-cases/ at build time. Rebuild with <code>python3 tool/build_refined_viewer.py</code> after adding cases.
    &nbsp;•&nbsp; <a href="#" id="openRaw">view raw in new tab</a>
  </div>
</main>

<script>
const ALL = __DATA__;
let currentPath = null;
let prettyMode = true;
let viewMode = 'zephyr';   // 'source' or 'zephyr'
let previewMode = 'objective';  // 'objective' or 'steps'

const sel = document.getElementById('sel');
const viewSel = document.getElementById('view');
const pre = document.getElementById('display');
const meta = document.getElementById('meta');
const filter = document.getElementById('filter');
const preview = document.getElementById('preview');

function populateSelect(filterText = '') {
  const q = filterText.toLowerCase().trim();
  sel.innerHTML = '';
  const groups = {};
  for (const p of Object.keys(ALL)) {
    if (q && !p.toLowerCase().includes(q)) continue;
    const cat = p.split('/')[1] || '(root)';
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(p);
  }
  const cats = Object.keys(groups).sort();
  for (const cat of cats) {
    const og = document.createElement('optgroup');
    og.label = cat;
    for (const p of groups[cat].sort()) {
      const opt = document.createElement('option');
      opt.value = p;
      opt.textContent = p;
      og.appendChild(opt);
    }
    sel.appendChild(og);
  }
  if (currentPath && ALL[currentPath]) {
    sel.value = currentPath;
  }
}

function formatJSON(obj, minify) {
  if (minify) return JSON.stringify(obj);
  return JSON.stringify(obj, null, 2);
}

function getDisplayObject(path) {
  const entry = ALL[path];
  if (!entry) return null;
  if (entry[viewMode]) return entry[viewMode];
  return entry; // fallback for old data shape
}

function show(path) {
  if (!path || !ALL[path]) return;
  currentPath = path;
  const obj = getDisplayObject(path);
  if (!obj) return;

  const txt = formatJSON(obj, !prettyMode);
  pre.textContent = txt;

  const viewLabel = viewMode === 'zephyr' ? 'Zephyr after-upload' : 'Source payload';
  const topKeys = (obj && typeof obj === 'object') ? Object.keys(obj).length : 0;
  meta.textContent = `${path}  ·  ${viewLabel}  ·  ${topKeys} top-level key(s)`;

  renderPreview(obj);
}

function getObjective(obj) {
  if (!obj) return null;
  if (typeof obj.objective === 'string' && obj.objective.trim().startsWith('<')) {
    return obj.objective;
  }
  if (obj && typeof obj === 'object') {
    // Handle source shape: { "AWPTCM-xxx": { objective: "...", ... } }
    for (const v of Object.values(obj)) {
      if (v && typeof v === 'object' && typeof v.objective === 'string' && v.objective.trim().startsWith('<')) {
        return v.objective;
      }
    }
  }
  return null;
}

function getSteps(obj) {
  if (!obj) return [];
  // Direct zephyr view shape
  if (obj.testScript && Array.isArray(obj.testScript.steps)) {
    return obj.testScript.steps;
  }
  // Source shape or other wrappers
  if (obj && typeof obj === 'object') {
    for (const v of Object.values(obj)) {
      if (v && typeof v === 'object' && v.testScript && Array.isArray(v.testScript.steps)) {
        return v.testScript.steps;
      }
    }
  }
  // Fallback: sometimes steps live at top level (rare)
  if (Array.isArray(obj.steps)) return obj.steps;
  return [];
}

function renderPreview(obj) {
  const controls = document.getElementById('preview-controls');
  const steps = getSteps(obj);
  const objectiveHtml = getObjective(obj);
  const hasObjective = !!(objectiveHtml && objectiveHtml.trim());
  const hasSteps = steps.length > 0;

  if (!hasObjective && !hasSteps) {
    controls.style.display = 'none';
    preview.style.display = 'none';
    preview.innerHTML = '';
    return;
  }

  controls.style.display = 'flex';

  if (previewMode === 'objective' && hasObjective) {
    preview.innerHTML = `
      <div style="font-size:12px;color:#8b95a7;margin-bottom:4px;">Objective preview (how it will render in Zephyr)</div>
      <div style="background:#f8f9fa;color:#111;border:1px solid #ccc;border-radius:6px;padding:10px 12px;font-size:13px;line-height:1.45;">
        ${objectiveHtml}
      </div>`;
    preview.style.display = 'block';
  } else if (previewMode === 'steps' && hasSteps) {
    let html = `<div style="font-size:12px;color:#8b95a7;margin-bottom:6px;">Test Steps preview (Zephyr step-by-step)</div>`;
    steps.forEach((s, i) => {
      const desc = (s.description || s.desc || '').trim();
      const exp = (s.expectedResult || s.expected || s.testData || '').trim();
      html += `
        <div style="margin:4px 0 8px; padding:8px 10px; background:#f8f9fa; border:1px solid #ddd; border-radius:6px; color:#111; font-size:13px; line-height:1.4;">
          <div style="font-weight:600; color:#444; margin-bottom:3px; font-size:12px;">Step ${i + 1}</div>
          <div>${desc || '<em>(no description)</em>'}</div>
          ${exp ? `<div style="margin-top:4px; color:#2e7d32; font-size:12px;"><strong>Expected:</strong> ${exp}</div>` : ''}
        </div>`;
    });
    preview.innerHTML = html;
    preview.style.display = 'block';
  } else {
    // Fallback: if requested mode has no content, show the other one
    if (hasObjective) {
      previewMode = 'objective';
      // re-render with objective
      preview.innerHTML = `
        <div style="font-size:12px;color:#8b95a7;margin-bottom:4px;">Objective preview (how it will render in Zephyr)</div>
        <div style="background:#f8f9fa;color:#111;border:1px solid #ccc;border-radius:6px;padding:10px 12px;font-size:13px;line-height:1.45;">
          ${objectiveHtml}
        </div>`;
      // ensure radio reflects it
      const objRadio = document.querySelector('input[name="pview"][value="objective"]');
      if (objRadio) objRadio.checked = true;
    } else if (hasSteps) {
      previewMode = 'steps';
      // (render steps inline to avoid recursion)
      let html = `<div style="font-size:12px;color:#8b95a7;margin-bottom:6px;">Test Steps preview (Zephyr step-by-step)</div>`;
      steps.forEach((s, i) => {
        const desc = (s.description || s.desc || '').trim();
        const exp = (s.expectedResult || s.expected || s.testData || '').trim();
        html += `
          <div style="margin:4px 0 8px; padding:8px 10px; background:#f8f9fa; border:1px solid #ddd; border-radius:6px; color:#111; font-size:13px; line-height:1.4;">
            <div style="font-weight:600; color:#444; margin-bottom:3px; font-size:12px;">Step ${i + 1}</div>
            <div>${desc || '<em>(no description)</em>'}</div>
            ${exp ? `<div style="margin-top:4px; color:#2e7d32; font-size:12px;"><strong>Expected:</strong> ${exp}</div>` : ''}
          </div>`;
      });
      preview.innerHTML = html;
      const stepsRadio = document.querySelector('input[name="pview"][value="steps"]');
      if (stepsRadio) stepsRadio.checked = true;
    }
    preview.style.display = 'block';
  }
}

function copy() {
  if (!currentPath) return;
  const txt = pre.textContent;
  navigator.clipboard.writeText(txt).then(() => {
    const b = document.getElementById('copy');
    const old = b.textContent;
    b.textContent = 'Copied!';
    setTimeout(() => b.textContent = old, 900);
  });
}

function download() {
  if (!currentPath) return;
  const blob = new Blob([pre.textContent], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = currentPath.split('/').pop() || 'case.json';
  a.click();
}

function toggleMode() {
  prettyMode = !prettyMode;
  document.getElementById('toggle').textContent = prettyMode ? 'Minify' : 'Pretty';
  if (currentPath) show(currentPath);
}

function openRaw() {
  if (!currentPath) return;
  const w = window.open('', '_blank');
  w.document.write('<pre style="font-family:monospace;white-space:pre-wrap;padding:16px">' +
    pre.textContent.replace(/&/g,'&amp;').replace(/</g,'&lt;') + '</pre>');
  w.document.close();
}

sel.addEventListener('change', () => show(sel.value));
viewSel.addEventListener('change', (e) => {
  viewMode = e.target.value;
  if (currentPath) show(currentPath);
});
document.getElementById('copy').addEventListener('click', copy);
document.getElementById('download').addEventListener('click', download);
document.getElementById('toggle').addEventListener('click', toggleMode);
document.getElementById('openRaw').addEventListener('click', (e) => { e.preventDefault(); openRaw(); });
filter.addEventListener('input', () => {
  populateSelect(filter.value);
  if (!currentPath || !sel.value) {
    const first = sel.querySelector('option');
    if (first) { sel.value = first.value; show(first.value); }
  }
});

// Preview mode toggle (Objective vs Test Steps)
document.querySelectorAll('input[name="pview"]').forEach(radio => {
  radio.addEventListener('change', (e) => {
    if (e.target.checked) {
      previewMode = e.target.value;
      if (currentPath) show(currentPath);
    }
  });
});

// init
populateSelect('');
viewMode = viewSel.value;
const checkedPreview = document.querySelector('input[name="pview"]:checked');
if (checkedPreview) previewMode = checkedPreview.value;

// pre-select first file
const firstOpt = sel.querySelector('option');
if (firstOpt) {
  sel.value = firstOpt.value;
  show(firstOpt.value);
}
</script>
</body>
</html>
"""

# Inject
page = (PAGE
        .replace("__SELECT_OPTIONS__", SELECT_HTML)
        .replace("__DATA__", DATA_JS))

with open(OUT, "w", encoding="utf-8") as f:
    f.write(page)

print(f"Wrote {OUT} with {len(data)} JSON files from refined-cases/")
print("Open the HTML file in any browser.")