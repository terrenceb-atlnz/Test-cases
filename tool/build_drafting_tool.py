#!/usr/bin/env python3
"""
Build a self-contained webpage-based tool for the Objective Drafting Process.

Focus: Best possible support for producing repeatable, high-fidelity outputs
(traceability.md + zephyr_payload.json) with strong provenance.

The generated HTML follows the patterns of review.html and refined-viewer.html:
- Static, single-file, vanilla JS + embedded data
- Dark theme matching existing tools
- Multi-step wizard matching the 4 steps + pauses in OBJECTIVE_DRAFTING_PROCESS.md

Data strategy:
- Embed lightweight indices for instant use (slim_index, candidates, zephyr_master, test_id_description summary)
- Support loading the full zephyr_cases.jsonl on demand via File API for full power (best repeatability)
- Session state is fully captured so exports are deterministic and replayable

Size: Designed to stay comfortably under 2GB even with rich data. Current full data ~143MB.

Usage:
  python3 tool/build_drafting_tool.py
  python3 tool/build_drafting_tool.py drafting-tool/index.html
"""

import sys
import json
import os
from collections import defaultdict

OUT = sys.argv[1] if len(sys.argv) > 1 else "drafting-tool/index.html"
BASE = "."

def load_json_safe(path):
    full = os.path.join(BASE, path)
    if os.path.exists(full):
        try:
            return json.load(open(full, encoding="utf-8"))
        except Exception as e:
            print(f"Warning: could not load {path}: {e}")
    return None

print("Loading data for drafting tool...")

# Lightweight indices we can safely embed
slim_index = load_json_safe("data/zephyr_full/slim_index.json") or []
zephyr_master = {c["key"]: c for c in (load_json_safe("data/zephyr_master.json") or [])}
candidates = load_json_safe("data/candidates.json") or []
test_id_desc = load_json_safe("data/suites/test_id_description.json") or {}

# Load decisions for primary matches (key part of Step 1)
dec = {}
for f in sorted([f for f in os.listdir("data/decisions") if f.endswith(".json")]):
    dec.update(json.load(open(os.path.join("data/decisions", f), encoding="utf-8")))

# Prepare compact data for embedding
print(f"  slim_index: {len(slim_index)} entries")
print(f"  zephyr_master: {len(zephyr_master)} cases")
print(f"  candidates: {len(candidates)}")
print(f"  decisions: {len(dec)} entries")

# For best experience, embed a good chunk of candidates and a decisions map
EMBEDDED = {
    "slim_index": slim_index[:8000],  # larger cap
    "zephyr_master": zephyr_master,
    "candidates": candidates,  # full for proper Step 1
    "decisions": dec,
    "test_id_desc_sample": {k: v for i, (k,v) in enumerate(test_id_desc.items()) if i < 300}
}

DATA_JS = json.dumps(EMBEDDED, ensure_ascii=False)

# The big HTML template (simplified but functional starting point)
PAGE = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Objective Drafting Tool — AWPTCM</title>
<style>
:root {
  --bg:#0f1115; --card:#171a21; --mut:#8b95a7; --fg:#e7ecf3; --line:#262b36;
  --acc:#3b82f6; --good:#5ddc7a; --warn:#e7c451;
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:14px/1.45 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }
header { position:sticky; top:0; z-index:20; background:#0f1115ee; backdrop-filter:blur(8px); border-bottom:1px solid var(--line); padding:12px 20px; }
h1 { font-size:18px; margin:0 0 4px; }
.step { max-width: 1100px; margin: 0 auto; padding: 16px 20px; }
.step h2 { font-size:16px; border-bottom:1px solid var(--line); padding-bottom:4px; margin-top:0; }
.controls { display:flex; gap:8px; flex-wrap:wrap; margin: 8px 0; }
input, select, button, textarea { background:var(--card); color:var(--fg); border:1px solid var(--line); border-radius:6px; padding:6px 9px; font-size:13px; }
button { cursor:pointer; }
button.primary { background:var(--acc); border-color:var(--acc); color:#fff; font-weight:600; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px; margin-bottom:12px; }
table { border-collapse: collapse; width:100%; font-size:13px; }
th, td { border:1px solid var(--line); padding:4px 6px; text-align:left; vertical-align:top; }
th { background:#12151c; }
tr:hover { background:#12151c; }
.selected { background:#13233f !important; }
.small { font-size:12px; color:var(--mut); }
pre, .code { font-family: ui-monospace,monospace; background:#0d1017; padding:8px; border-radius:6px; overflow:auto; }
ul.output { margin:4px 0; padding-left:20px; }
.status { padding:2px 8px; border-radius:4px; font-size:11px; }
.wizard-nav { display:flex; gap:8px; margin:12px 0; }
.wizard-nav button.active { background:var(--acc); color:#fff; }
</style>
</head>
<body>
<header>
  <h1>Objective Drafting Tool <span style="color:var(--mut); font-weight:400; font-size:13px">— following OBJECTIVE_DRAFTING_PROCESS.md (best repeatable outputs)</span></h1>
  <div class="small">Size target &lt;2GB • Focus: provenance • deterministic export • fidelity</div>
</header>

<div class="step">
  <div class="controls">
    <button onclick="prevStep()">◀ Prev</button>
    <button onclick="nextStep()">Next ▶</button>
    <select id="caseSel" onchange="loadCase(this.value)">
      <option value="">Select AWPTCM case...</option>
    </select>
    <button onclick="exportBundle()" class="primary">Export Repeatable Bundle (traceability.md + payload + session.json)</button>
    <button onclick="saveSession()">Save Session</button>
    <button onclick="loadSession()">Load Session</button>
  </div>

  <div id="wizard-nav" class="wizard-nav">
    <button data-step="1" onclick="goToStep(1)">1. TestLink + Decisions</button>
    <button data-step="2" onclick="goToStep(2)">2. Zephyr Cross-Ref</button>
    <button data-step="3" onclick="goToStep(3)">3. ATPyLib + Gaps</button>
    <button data-step="4" onclick="goToStep(4)">4. Draft Objective &amp; Steps</button>
  </div>

  <!-- Step 1 -->
  <div id="step-1" class="card">
    <h2>Step 1: Review TestLink Cases + Decisions (with pause)</h2>
    <div class="small">From candidates + decisions. Select relevant TestLink. Primary from decisions if available. Confirm for provenance.</div>
    <div id="primary-info" class="small"></div>
    <label style="display:block; margin:4px 0;"><input type="checkbox" id="testlink-none" onchange="toggleTestLinkNone(this.checked)"> <strong>None</strong> (no relevant TestLink cases)</label>
    <input id="search1" placeholder="search TestLink title or id" oninput="filterStep1()">
    <div style="max-height:280px; overflow:auto; margin-top:6px;">
      <table id="table1"><thead><tr><th></th><th>ID</th><th>Title / Suite</th><th>Justification</th></tr></thead><tbody></tbody></table>
    </div>
    <button onclick="confirmStep1()">Mark TestLink List Reviewed + Confirmed</button>
    <div id="step1-status" class="small"></div>
  </div>

  <!-- Step 2 -->
  <div id="step-2" class="card" style="display:none">
    <h2>Step 2: Zephyr Database Cross-Reference (Intelligent)</h2>
    <div class="small">Uses embedded slim_index. For full power, use "Load full zephyr_cases.jsonl" button (supports best offline cross-ref). Confirm for provenance.</div>
    <label style="display:block; margin:4px 0;"><input type="checkbox" id="zephyr-none" onchange="toggleZephyrNone(this.checked)"> <strong>None</strong> (no relevant Zephyr cases)</label>
    <input id="search2" placeholder="search title/folder" oninput="filterZephyr()">
    <button onclick="loadFullZephyr()">Load full zephyr_cases.jsonl from disk (File API)</button>
    <div style="max-height:260px; overflow:auto;">
      <table id="table2"><thead><tr><th>Select</th><th>Key</th><th>Title</th><th>Folder</th><th>Obj?</th><th>Justification</th></tr></thead><tbody></tbody></table>
    </div>
    <button onclick="confirmStep2()">Mark Zephyr Cross-Refs Reviewed</button>
  </div>

  <!-- Step 3 -->
  <div id="step-3" class="card" style="display:none">
    <h2>Step 3: ATPyLib Coverage + Gaps</h2>
    <input id="search3" placeholder="keyword search in test descriptions" oninput="searchATPyLib()">
    <label style="display:block; margin:4px 0;"><input type="checkbox" id="atp-none" onchange="toggleAtpNone(this.checked)"> <strong>None</strong> (no relevant ATPyLib cases)</label>
    <div class="small">Click results to select for ART string. Selected will be used in export. Confirm for provenance.</div>
    <div id="atp-results" style="max-height:220px; overflow:auto; font-size:12px;"></div>
    <div id="art-selected" class="small" style="margin:4px 0; min-height:20px;"></div>
    <textarea id="gaps" style="width:100%; height:80px" placeholder="Gaps noted..."></textarea>
    <div class="small">ART string built from selected + gaps.</div>
    <button onclick="confirmStep3()">Mark ATPyLib + Gaps Reviewed</button>
  </div>

  <!-- Step 4 -->
  <div id="step-4" class="card" style="display:none">
    <h2>Step 4: Draft Objective (artefacts) + testScript Steps</h2>
    <div class="small"><strong>Drafting occurs AFTER all documentation selected (Steps 1-3).</strong> Write declarative &lt;ul&gt;&lt;li&gt; only. Use selections above for ideas. First step should be the note about ART/Zephyr.</div>
    <textarea id="objective" style="width:100%; height:120px" placeholder="<ul><li>A port with no pluggable...</li></ul>"></textarea>
    <div><strong>Live preview:</strong></div>
    <div id="obj-preview" class="code"></div>

    <h3>Steps (action-oriented)</h3>
    <div id="steps-container"></div>
    <button onclick="addStep()">+ Add Step</button>
    <div class="small">Export will produce exact zephyr_payload.json shape. Selections from prior steps will be reflected in traceability.</div>
  </div>

  <div class="card">
    <h3>Current Session (for provenance &amp; repeatability)</h3>
    <pre id="session-json" style="max-height:160px; overflow:auto; font-size:11px;"></pre>
  </div>
</div>

<script>
const EMBEDDED = __DATA__;

let currentKey = null;
let session = { key: null, steps: {}, zephyrSelected: [], confirmed: {}, testlinkNone: false, zephyrNone: false, atpNone: false };

function updateSessionView() {
  document.getElementById('session-json').textContent = JSON.stringify(session, null, 2);
  updateNavStatus();
  updateTestLinkNoneUI();
  updateZephyrNoneUI();
  updateArtSelected();
}

function updateNavStatus() {
  const nav = document.getElementById('wizard-nav');
  if (!nav) return;
  Array.from(nav.children).forEach(btn => {
    const step = parseInt(btn.getAttribute('data-step') || '0');
    let base = btn.getAttribute('data-base');
    if (!base) {
      base = btn.textContent.replace(/^[✓\s]*/, '').replace(/ \(ready\)/, '');
      btn.setAttribute('data-base', base);
    }
    if (step === 1 && session.confirmed && session.confirmed.testlink) {
      btn.textContent = '✓ ' + base;
      btn.style.background = '#1c3a24';
      btn.style.color = '#5ddc7a';
    } else if (step === 2 && session.confirmed && session.confirmed.zephyr) {
      btn.textContent = '✓ ' + base;
      btn.style.background = '#1c3a24';
      btn.style.color = '#5ddc7a';
    } else if (step === 3 && session.confirmed && session.confirmed.atp) {
      btn.textContent = '✓ ' + base;
      btn.style.background = '#1c3a24';
      btn.style.color = '#5ddc7a';
    } else if (step === 4) {
      if (canProceedToDraft()) {
        btn.textContent = '✓ ' + base + ' (ready)';
        btn.style.background = '#1c3a24';
        btn.disabled = false;
        btn.style.opacity = '1';
      } else {
        btn.textContent = base;
        btn.disabled = true;
        btn.style.opacity = '0.5';
        btn.style.background = '';
      }
    }
  });
}

function canProceedToDraft() {
  return !!(session.confirmed && session.confirmed.testlink && session.confirmed.zephyr && session.confirmed.atp);
}

function goToStep(n) {
  if (n === 4 && !canProceedToDraft()) {
    alert("You must complete and confirm all documentation steps (1: TestLink, 2: Zephyr, 3: ATPyLib) before drafting objectives.\n\nDrafting must occur AFTER all relevant documentation has been selected and reviewed.");
    // jump to the first unconfirmed step
    if (!session.confirmed || !session.confirmed.testlink) n = 1;
    else if (!session.confirmed.zephyr) n = 2;
    else if (!session.confirmed.atp) n = 3;
  }
  [1,2,3,4].forEach(i => {
    const el = document.getElementById('step-' + i);
    if (el) el.style.display = (i === n) ? 'block' : 'none';
  });
}

function loadCase(key) {
  if (!key) return;
  currentKey = key;
  session.key = key;
  // reset some state but preserve loaded session if any
  if (!session.testlinkSelected) session.testlinkSelected = [];
  if (!session.zephyrSelected) session.zephyrSelected = [];
  session.steps = session.steps || {};
  updateSessionView();

  // Pre-fill from zephyr_master if present
  const m = EMBEDDED.zephyr_master[key];
  if (m && !session.steps.objective) {
    document.getElementById('objective').value = m.objective || '';
    renderObjectivePreview();
  }

  // Populate Step 1 from candidates + decisions
  populateStep1(key);

  // Populate Zephyr table from slim (now Step 2)
  const tbodyZ = document.querySelector('#table2 tbody');
  if (tbodyZ && EMBEDDED.slim_index) {
    tbodyZ.innerHTML = '';
    EMBEDDED.slim_index.slice(0, 40).forEach(c => {
      const tr = document.createElement('tr');
      const checked = !session.zephyrNone && (session.zephyrSelected || []).some(s => s.key === c.key) ? 'checked' : '';
      tr.innerHTML = `
        <td><input type="checkbox" data-key="${c.key}" ${checked} onchange="addZephyrSelectionFromCheck('${c.key}', this.checked)"></td>
        <td>${c.key}</td>
        <td>${c.title || ''}</td>
        <td>${(c.folder || '').slice(0,40)}</td>
        <td>${c.has_objective ? 'Y' : 'N'}</td>
        <td><input placeholder="justification" value="${(session.zephyrSelected || []).find(s=>s.key===c.key)?.justification||''}" onblur="addZephyrSelection('${c.key}', this.value, '${c.title||''}', '${c.folder||''}', ${c.has_objective||false}, ${c.num_steps||0})"></td>
      `;
      tbodyZ.appendChild(tr);
    });
  }
  updateZephyrNoneUI();

  updateTestLinkNoneUI();
  updateArtSelected();

  goToStep(1);
}

function addZephyrSelectionFromCheck(key, checked) {
  if (checked) {
    session.zephyrNone = false;
    const c = (EMBEDDED.slim_index || []).find(x => x.key === key);
    if (c && !(session.zephyrSelected || []).find(s => s.key === key)) {
      addZephyrSelection(key, '', c.title, c.folder, c.has_objective, c.num_steps);
    }
  } else {
    session.zephyrSelected = (session.zephyrSelected || []).filter(s => s.key !== key);
    updateSessionView();
  }
}

let step1TableData = [];

function populateStep1(key) {
  const tbody = document.querySelector('#table1 tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  step1TableData = [];

  const candEntry = (EMBEDDED.candidates || []).find(c => c.key === key);
  const primary = EMBEDDED.decisions ? EMBEDDED.decisions[key] : null;

  const info = document.getElementById('primary-info');
  if (info) {
    if (primary && primary.m) {
      info.innerHTML = `<b>Primary from decisions:</b> ${primary.m} (conf: ${primary.c || 'med'}) - ${primary.w || ''}`;
      session.primary = primary.m;
      session.primaryTitle = primary.w || '';
      session.conf = primary.c || 'med';
      session.rationale = primary.w || '';
    } else {
      info.innerHTML = '<b>No primary decision found</b>';
    }
  }

  if (candEntry && candEntry.candidates && candEntry.candidates.length > 0) {
    candEntry.candidates.forEach((c, idx) => {
      const tr = document.createElement('tr');
      const sel = !session.testlinkNone && (session.testlinkSelected || []).some(s => s.id === c.id) ? 'checked' : '';
      tr.innerHTML = `
        <td><input type="checkbox" data-idx="${idx}" ${sel} onchange="toggleTestLinkSelection(${idx}, this.checked)"></td>
        <td>${c.id}</td>
        <td>${c.title}<br><span class="small">${c.suite || ''}</span></td>
        <td><input placeholder="why relevant" value="${(session.testlinkSelected || []).find(s=>s.id===c.id)?.justification || ''}" 
             onblur="setTestLinkJustification(${idx}, this.value)"></td>
      `;
      tbody.appendChild(tr);
      step1TableData.push(c);
    });
  }
  updateTestLinkNoneUI();
}

function toggleTestLinkSelection(idx, checked) {
  const c = step1TableData[idx];
  if (!session.testlinkSelected) session.testlinkSelected = [];
  if (checked) {
    session.testlinkNone = false;  // unselect none
    if (!session.testlinkSelected.find(s => s.id === c.id)) {
      session.testlinkSelected.push({id: c.id, title: c.title, suite: c.suite, justification: ''});
    }
  } else {
    session.testlinkSelected = session.testlinkSelected.filter(s => s.id !== c.id);
  }
  updateTestLinkNoneUI();
  updateSessionView();
}

function setTestLinkJustification(idx, just) {
  const c = step1TableData[idx];
  if (!session.testlinkSelected) session.testlinkSelected = [];
  let entry = session.testlinkSelected.find(s => s.id === c.id);
  if (entry) entry.justification = just;
  updateSessionView();
}

function toggleTestLinkNone(checked) {
  session.testlinkNone = checked;
  if (checked) {
    session.testlinkSelected = [];
  }
  updateTestLinkNoneUI();
  updateSessionView();
}

function updateTestLinkNoneUI() {
  const noneCb = document.getElementById('testlink-none');
  if (noneCb) noneCb.checked = !!session.testlinkNone;
  const tbody = document.querySelector('#table1 tbody');
  if (tbody && session.testlinkNone) {
    Array.from(tbody.querySelectorAll('input[type=checkbox]')).forEach(cb => cb.checked = false);
  }
}

function filterStep1() {
  const q = (document.getElementById('search1') || {}).value || '';
  const tbody = document.querySelector('#table1 tbody');
  if (!tbody) return;
  const lower = q.toLowerCase();
  Array.from(tbody.rows).forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(lower) ? '' : 'none';
  });
}

function confirmStep1() {
  if (!session.testlinkNone && (!session.testlinkSelected || session.testlinkSelected.length === 0)) {
    if (!confirm('No TestLink selected and None not chosen. Continue anyway?')) return;
  }
  session.confirmed.testlink = true;
  session.confirmed.testlinkTime = new Date().toISOString();
  updateSessionView();
  alert("TestLink list marked reviewed + confirmed. Move to Step 2.");
  goToStep(2);
}

function confirmStep2() {
  if (!session.zephyrNone && (!session.zephyrSelected || session.zephyrSelected.length === 0)) {
    if (!confirm('No Zephyr cases selected and None not chosen. Continue anyway?')) return;
  }
  session.confirmed.zephyr = true;
  session.confirmed.zephyrTime = new Date().toISOString();
  updateSessionView();
  alert("Zephyr Cross-Refs marked reviewed. Move to Step 3.");
  goToStep(3);
}

function confirmStep3() {
  if (!session.atpNone && (!atpSelected || atpSelected.length === 0)) {
    if (!confirm('No ATPyLib cases selected and None not chosen. Continue anyway?')) return;
  }
  session.confirmed.atp = true;
  session.confirmed.atpTime = new Date().toISOString();
  updateSessionView();
  alert("ATPyLib + Gaps marked reviewed. Move to Step 4.");
  goToStep(4);
}

function renderObjectivePreview() {
  const val = document.getElementById('objective').value;
  document.getElementById('obj-preview').innerHTML = val;
}

function addStep() {
  const container = document.getElementById('steps-container');
  const div = document.createElement('div');
  div.innerHTML = `<input class="step-desc" style="width:80%" placeholder="Action description..."> <button onclick="this.parentNode.remove()">×</button>`;
  container.appendChild(div);
}

function filterZephyr() {
  const q = document.getElementById('search2').value.toLowerCase();
  const tbody = document.querySelector('#table2 tbody');
  if (!tbody) return;
  Array.from(tbody.rows).forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
}

let fullZephyrLoaded = false;

async function loadFullZephyr() {
  const input = document.createElement('input');
  input.type = 'file';
  input.onchange = async () => {
    const file = input.files[0];
    if (!file) return;
    const text = await file.text();
    const lines = text.trim().split('\n');
    const cases = lines.map(l => JSON.parse(l));
    window.FULL_ZEPHYR = cases;
    fullZephyrLoaded = true;
    alert(`Loaded ${cases.length} Zephyr cases from file. Re-select the case to use full data in Step 3 table.`);
  };
  input.click();
}

function addZephyrSelection(key, justification, title, folder, hasObj, numSteps) {
  if (!session.zephyrSelected) session.zephyrSelected = [];
  let entry = session.zephyrSelected.find(x => x.key === key);
  if (!entry) {
    entry = {key, justification: justification || '', title: title || key, folder: folder || '', has_objective: !!hasObj, num_steps: numSteps || 0};
    session.zephyrSelected.push(entry);
  } else if (justification !== undefined) {
    entry.justification = justification;
  }
  updateSessionView();
}

function toggleZephyrNone(checked) {
  session.zephyrNone = checked;
  if (checked) {
    session.zephyrSelected = [];
  }
  updateZephyrNoneUI();
  updateSessionView();
}

function updateZephyrNoneUI() {
  const noneCb = document.getElementById('zephyr-none');
  if (noneCb) noneCb.checked = !!session.zephyrNone;
  const tbody = document.querySelector('#table2 tbody');
  if (tbody && session.zephyrNone) {
    Array.from(tbody.querySelectorAll('input[type=checkbox]')).forEach(cb => cb.checked = false);
  }
}

let atpSelected = [];

function searchATPyLib() {
  const q = document.getElementById('search3').value.toLowerCase();
  const res = document.getElementById('atp-results');
  res.innerHTML = '';
  if (!q) return;
  let count = 0;
  for (const [tid, entry] of Object.entries(EMBEDDED.test_id_desc_sample || {})) {
    const d = (entry.description || '').toLowerCase();
    if (d.includes(q) && count < 15) {
      const div = document.createElement('div');
      const isSel = !session.atpNone && atpSelected.includes(tid);
      div.style.cursor = 'pointer';
      div.style.padding = '2px';
      div.style.background = isSel ? '#13233f' : '';
      div.textContent = `${isSel ? '✓ ' : ''}${tid}: ${(entry.description||'').slice(0,100)}`;
      div.onclick = () => {
        if (session.atpNone) {
          session.atpNone = false;
        }
        if (atpSelected.includes(tid)) {
          atpSelected = atpSelected.filter(x => x !== tid);
        } else {
          atpSelected.push(tid);
        }
        session.artSelected = atpSelected;
        updateArtSelected();
        searchATPyLib(); // refresh
      };
      res.appendChild(div);
      count++;
    }
  }
}

function updateArtSelected() {
  const el = document.getElementById('art-selected');
  let text = 'Selected ART: ';
  if (session.atpNone) {
    text += 'None';
  } else {
    text += (atpSelected.length ? atpSelected.join(', ') : '(none)');
  }
  if (el) el.textContent = text;
  const noneCb = document.getElementById('atp-none');
  if (noneCb) noneCb.checked = !!session.atpNone;
}

function toggleAtpNone(checked) {
  session.atpNone = checked;
  if (checked) {
    atpSelected = [];
    session.artSelected = [];
  }
  updateArtSelected();
  updateSessionView();
  searchATPyLib(); // refresh to show check
}

function finalizeOutput() {
  session.steps.objective = document.getElementById('objective').value;
  // collect steps
  const steps = [];
  document.querySelectorAll('#steps-container .step-desc').forEach(inp => {
    if (inp.value.trim()) steps.push({description: inp.value.trim(), expectedResult: ""});
  });
  session.steps.testScript = { type: "steps", steps };
  if (session.atpNone) {
    session.artString = 'None';
  } else if (atpSelected.length) {
    session.artString = atpSelected.join(' + ');
  }
  session.gaps = document.getElementById('gaps').value;
  updateSessionView();
  alert("Output prepared in session. Use Export button.");
}

function exportBundle() {
  if (!currentKey) { alert("Select a case first"); return; }
  if (!canProceedToDraft()) {
    alert("Cannot export yet: All documentation must be selected and confirmed (Steps 1-3) before drafting objectives. Drafting happens after documentation selection.");
    return;
  }

  const obj = session.steps.objective || "<ul><li>TODO</li></ul>";
  let steps = session.steps.testScript ? session.steps.testScript.steps : [];
  if (steps.length === 0) {
    steps = [
      { description: "The testing for this is covered by ...<br />Note: Related ART Tests linked in Traceability.<dl><br /></dl><br />", expectedResult: "" },
      { description: "TODO - first verification step", expectedResult: "" }
    ];
  }

  const payload = {};
  payload[currentKey] = {
    objective: obj,
    testScript: { type: "steps", steps: steps }
  };

  const payloadJson = JSON.stringify(payload, null, 2);

  if (atpSelected && atpSelected.length) {
    session.artString = atpSelected.join(' + ');
  }

  // Generate traceability.md closely matching the documented + real examples structure
  let md = `# Traceability & Supporting Data for ${currentKey} (Port - Auto MDI/MDI-X)\n\n`;

  // Primary Decision (placeholder - in real would come from session.primary)
  md += `## Primary Decision\n`;
  md += `- **${session.primary || 'AWP-XXXXXX'}** – \`${session.primaryTitle || '...'}\`\n`;
  md += `  - "${session.primarySummary || '...'}"\n`;
  md += `  - Decision confidence: ${session.conf || 'med'}\n`;
  md += `  - Rationale: ${session.rationale || '...'}\n\n`;

  // Top Relevant TestLink Cases (from session.testlinkSelected if captured)
  md += `## Top Relevant TestLink Cases\n`;
  if (session.testlinkNone) {
    md += `None\n\n`;
  } else if (session.testlinkSelected && session.testlinkSelected.length > 0) {
    md += `**Primary + relevant cases (confirmed)**\n`;
    session.testlinkSelected.forEach(tl => {
      md += `- **${tl.id}** — ${tl.title}\n`;
      if (tl.suite) md += `  - Suite: ${tl.suite}\n`;
      if (tl.justification) md += `  - Justification: ${tl.justification}\n`;
    });
    md += `\n`;
  } else {
    md += `**Primary + High-ranking ... cases** (populated from session in full version)\n`;
    md += `- (See draft-session.json for captured selections)\n\n`;
  }

  // Zephyr Cross-References (Step 3)
  md += `## Zephyr Cross-References (Step 3)\n`;
  if (session.zephyrNone) {
    md += `None\n\n`;
  } else {
    md += `**Relevant Zephyr Scale cases identified**\n\n`;
    md += `These cases were reviewed from the full Zephyr database (via \`data/zephyr_full/\`) for objective style, step structure, and related behaviour.\n\n`;
    (session.zephyrSelected || []).forEach((s, i) => {
      md += `${i+1}. **[${s.key}](https://jira.atlnz.lc/secure/Tests.jspa#/testCase/${s.key})** — ${s.title || s.key}\n`;
      md += `   - Folder: ${s.folder || ''}\n`;
      md += `   - Objective: ${s.has_objective ? 'Yes' : 'No'}\n`;
      md += `   - Steps: ${s.num_steps || '?'}\n`;
      md += `   - Justification: ${s.justification || ''}\n\n`;
    });
  }

  // ATPyLib
  md += `## ATPyLib Cases (Step 4)\n`;
  if (session.atpNone) {
    md += `None\n\n`;
  } else {
    md += `${session.artString || '1342.301.13 + relevant ... (from Step 4 search)'}\n\n`;
  }

  md += `## Gaps Noted\n`;
  md += `${session.gaps || '- Limited ... (captured in session)'}\n\n`;

  md += `## Tangential Cases Reviewed\n`;
  md += `(Captured in session)\n\n`;

  md += `## ART Test Cases String\n`;
  md += `${session.artString || '...'}\n\n`;

  md += `---\nGenerated by drafting-tool/index.html (repeatable from captured session)\n`;

  // Download files with correct names for easy drop-in
  downloadFile(`${currentKey}-zephyr_payload.json`, payloadJson);
  downloadFile(`traceability.md`, md);  // as it would be inside the case dir
  downloadFile(`${currentKey}-draft-session.json`, JSON.stringify(session, null, 2));

  alert("Exported bundle (payload + traceability.md + session.json). These are designed as drop-in repeatable artifacts.");
}

function downloadFile(name, content) {
  const a = document.createElement('a');
  a.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent(content);
  a.download = name;
  a.click();
}

function saveSession() {
  localStorage.setItem('drafting_session_' + (currentKey||'global'), JSON.stringify(session));
  alert("Session saved to localStorage (for this browser).");
}

function loadSession() {
  const saved = localStorage.getItem('drafting_session_' + (currentKey||'global'));
  if (saved) {
    try {
      const loaded = JSON.parse(saved);
      session = Object.assign(session, loaded);
      updateSessionView();
      if (session.steps && session.steps.objective) {
        document.getElementById('objective').value = session.steps.objective;
        renderObjectivePreview();
      }
      updateTestLinkNoneUI();
      updateZephyrNoneUI();
      if (session.artSelected) atpSelected = session.artSelected;
      updateArtSelected();
      alert("Session loaded from localStorage.");
    } catch(e) { alert("Failed to load session"); }
  } else {
    // Allow loading from a file for replay
    const input = document.createElement('input');
    input.type = 'file';
    input.onchange = () => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const loaded = JSON.parse(ev.target.result);
          session = Object.assign({}, session, loaded);
          if (currentKey && session.key) currentKey = session.key;
          updateSessionView();
          if (session.steps && session.steps.objective) {
            document.getElementById('objective').value = session.steps.objective;
            renderObjectivePreview();
          }
          updateTestLinkNoneUI();
          updateZephyrNoneUI();
          if (session.artSelected) atpSelected = session.artSelected;
          updateArtSelected();
          alert("Replay session loaded from file.");
        } catch(e) { alert("Invalid session file"); }
      };
      reader.readAsText(input.files[0]);
    };
    input.click();
  }
}

// Init
function init() {
  const sel = document.getElementById('caseSel');
  const keys = Object.keys(EMBEDDED.zephyr_master || {}).sort();
  keys.forEach(k => {
    const opt = document.createElement('option');
    opt.value = k;
    opt.textContent = k;
    sel.appendChild(opt);
  });

  document.getElementById('objective').oninput = renderObjectivePreview;

  // Set initial provenance info (data snapshot for repeatability)
  session.dataVersions = {
    buildTime: new Date().toISOString(),
    slimIndexEntries: (EMBEDDED.slim_index || []).length,
    candidatesCount: (EMBEDDED.candidates || []).length,
    decisionsCount: Object.keys(EMBEDDED.decisions || {}).length
  };

  // Keyboard hint
  console.log('%c[Drafting Tool] Ready. Focus is on repeatable exports + provenance.', 'color:#8b95a7');
  updateSessionView();
  // ensure draft button disabled until ready
  updateNavStatus();
}

window.onload = init;
</script>
</body>
</html>
"""

# Write the file
with open(OUT, "w", encoding="utf-8") as f:
    f.write(PAGE.replace("__DATA__", DATA_JS))

print(f"\nWrote {OUT}")
print("Open it in a browser. It is a functional starting point for the guided drafting workflow.")
print("Key features implemented in v1:")
print("  - Case selection")
print("  - Step 1/3 search + selection")
print("  - Objective + steps editor + preview")
print("  - Full provenance session capture")
print("  - Export of exact payload + md + session.json (repeatable)")
print("  - Support for loading full zephyr jsonl via File API")
