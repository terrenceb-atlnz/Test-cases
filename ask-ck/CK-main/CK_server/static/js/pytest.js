// PyTest Creator: the full 8-step gated flow.
import { registerActions } from './actions.js';
import { S } from './state.js';
import { dataArgs, escapeHtml, setButtonBusy, flashButtonDone } from './dom-helpers.js';
import { refreshCaseSelects } from './cases.js';
import { goToPanel } from './nav.js';
import { recordLLMDebug } from './llm-debug.js';
import { registerProvenance, renderProvenanceBlock, seedProvenanceFromStep } from './provenance.js';

// Mount the shared LLM Provenance block into a per-panel container, wired to the
// panel's endpoint (dry_run for Refresh). `stepProv` seeds the last real call's
// prompt/response from the session when present.
function mountPtProvenance(mountId, panelId, endpoint, stepProv) {
  const mount = document.getElementById(mountId);
  if (!mount || !S.ptCase) return;
  registerProvenance(panelId, () => endpoint.replace('{key}', encodeURIComponent(S.ptCase.key)), () => ({}));
  if (stepProv) seedProvenanceFromStep(panelId, stepProv);
  mount.innerHTML = renderProvenanceBlock(panelId);
}

export let ptSession = null;          // server session for S.ptCase.key
let ptCaseInfo = null;         // {title, group_display, objective, steps} from load_case
let ptRunPoll = null;          // setInterval handle while a run is active

const PT_API = '/api/pytest-create';

// `opts` may carry two non-fetch fields, stripped before the request:
//   btn       — the triggering button; gets busy spinner + disable + ✓/✗ flash
//   busyLabel — label shown in the button while in flight (default 'Working…')
// The busy guard also stops a second click from stacking a duplicate LLM call.
async function ptApi(path, opts = {}, statusEl = null) {
  const { btn = null, busyLabel, ...fetchOpts } = opts;
  if (btn && !setButtonBusy(btn, true, { label: busyLabel || 'Working…' })) return null;
  if (statusEl) statusEl.textContent = 'Working…';
  let ok = false;
  try {
    const r = await fetch(PT_API + path, Object.assign({
      headers: { 'Content-Type': 'application/json' },
    }, fetchOpts));
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      const msg = d.detail || `HTTP ${r.status}`;
      if (statusEl) statusEl.textContent = '⚠ ' + msg;
      else alert('PyTest Creator: ' + msg);
      return null;
    }
    if (statusEl) statusEl.textContent = '';
    ok = true;
    return d;
  } catch (e) {
    if (statusEl) statusEl.textContent = '⚠ ' + e;
    else alert('PyTest Creator: ' + e);
    return null;
  } finally {
    if (btn) { setButtonBusy(btn, false); flashButtonDone(btn, ok); }
  }
}

function ptStatusEl(id) { return document.getElementById(id); }

function ptRequireCase() {
  if (!S.ptCase.key || !ptSession) {
    alert('Load a case first (PyTest Creator → 1. Cases).');
    goToPanel('panel-pt-cases');
    return false;
  }
  return true;
}

async function ptRefreshCases() {
  const st = ptStatusEl('pt-load-status');
  const btn = document.getElementById('pt-refresh-btn');
  if (btn) btn.disabled = true;
  if (st) st.textContent = 'Refreshing…';
  const before = S.ptCase.key;
  // refreshCaseSelects re-scans the Generator cases AND (at its end) refreshes the two
  // PyTest Creator dropdowns from /api/pytest-create/pt_cases, preserving the selection.
  await refreshCaseSelects(before);
  const openSel = document.getElementById('ptCaseSelOpen');
  const doneSel = document.getElementById('ptCaseSelDone');
  const nOpen = openSel ? Array.from(openSel.options).filter(o => o.value).length : 0;
  const nDone = doneSel ? Array.from(doneSel.options).filter(o => o.value).length : 0;
  if (st) st.textContent = `Case lists refreshed — ${nOpen} open/partial, ${nDone} complete. `
    + 'A case appears here only once it has a refined zephyr_payload.json (export it in the Objective/Test Case Generator first); it moves to Complete once its PyTest script passes Final Validation (step 8).';
  if (btn) btn.disabled = false;
}

async function ptLoadCase() {
  if (!S.ptCase.key) { alert('Select a completed case first.'); return; }
  const st = ptStatusEl('pt-load-status');
  const d = await ptApi(`/load_case/${S.ptCase.key}`, { method: 'POST' }, st);
  if (!d) return;
  ptSession = d.session;
  ptCaseInfo = { title: d.case_title, group_display: d.group_display,
                 objective: d.objective, steps: d.steps };
  updatePtBadges();
  goToPanel('panel-pt-seq');
}

async function ptRefreshSession() {
  if (!S.ptCase.key) return;
  const d = await ptApi(`/session/${S.ptCase.key}`);
  if (d) { ptSession = d.session; updatePtBadges(); }
}

function updatePtBadges() {
  const s = ptSession || {};
  document.querySelectorAll('#nav-pt .sidebar-nav-item[data-pt-step]').forEach(item => {
    const n = item.getAttribute('data-pt-step');
    const step = s['step' + n] || {};
    const conf = n === '8' ? !!(step.confirmed && step.validated) : !!step.confirmed;
    let b = item.querySelector('.nav-badge');
    if (conf && !b) {
      b = document.createElement('span');
      b.className = 'nav-badge badge badge-success';
      b.textContent = '✓';
      item.appendChild(b);
    } else if (!conf && b) b.remove();
  });
  for (let n = 2; n <= 8; n++) {
    const el = document.getElementById('pt-badge-' + n);
    if (el) el.classList.toggle('hidden', !((s['step' + n] || {}).confirmed));
  }
}

async function ptConfirm(step) {
  if (!ptRequireCase()) return;
  const d = await ptApi(`/confirm_step/${S.ptCase.key}/${step}`, { method: 'POST', body: '{}' });
  if (d) { ptSession = d.session; updatePtBadges(); }
}

// --- Step 2: Sequence -------------------------------------------------------

export function renderPtSeqPanel() {
  const caseEl = document.getElementById('pt-seq-case');
  if (!S.ptCase.key || !ptSession) {
    caseEl.innerHTML = '<em class="review-empty">No case loaded — go to </em>'
      + '<a href="#" data-action="goToPanel" data-args="[&quot;panel-pt-cases&quot;]">1. Cases</a>.';
    document.getElementById('pt-seq-list').innerHTML = '';
    return;
  }
  caseEl.innerHTML = `<b>Case:</b> <span class="sel-label">${escapeHtml(S.ptCase.key)}</span>`
    + (ptCaseInfo && ptCaseInfo.title ? ` — ${escapeHtml(ptCaseInfo.title)}` : '')
    + (ptCaseInfo && ptCaseInfo.steps ? ` <span class="justification-note">(${ptCaseInfo.steps.length} refined steps)</span>` : '');
  ptRenderRefinedSteps((ptCaseInfo && ptCaseInfo.steps) || []);
  ptRenderSequenceCached(((ptSession.step2 || {}).sequence) || []);
  const notes = (ptSession.step2 || {}).notes;
  if (notes) ptStatusEl('pt-seq-status').textContent = 'LLM notes: ' + notes;
  mountPtProvenance('pt-seq-prov', 'panel-pt-seq', '/api/pytest-create/extract_sequence/{key}', (ptSession.step2 || {}).provenance);
  updatePtBadges();
}

// The refined test steps as loaded — the "before" the LLM re-sequences. This is the
// exact list the extractor indexes with zephyr_step_idx (traceability note already
// stripped server-side), so the "from" column in the sequence table lines up 1:1.
function ptRenderRefinedSteps(steps) {
  const el = document.getElementById('pt-seq-refined');
  if (!el) return;
  if (!steps.length) {
    el.innerHTML = '<em class="review-empty">No refined steps on this case.</em>';
    return;
  }
  let html = '<div class="justification-note mb-1">Refined test steps (as loaded — the order the manual case is written in):</div>';
  html += '<table class="table"><thead><tr><th style="width:24px">#</th><th>Description</th></tr></thead><tbody>';
  steps.forEach((s, i) => {
    html += `<tr>
      <td>${i + 1}</td>
      <td style="font-size:11px">${escapeHtml(s.description || '')}</td>
    </tr>`;
  });
  html += '</tbody></table>';
  el.innerHTML = html;
}

function ptRenderSequence(seq) {
  const el = document.getElementById('pt-seq-list');
  if (!seq.length) {
    el.innerHTML = '<em class="review-empty">No sequence yet — run Extract Sequence (LLM).</em>';
    return;
  }
  // Flag when the LLM's execution order differs from the manual step order.
  const froms = seq.map(s => s.zephyr_step_idx).filter(v => typeof v === 'number');
  const reordered = froms.length > 1 && froms.some((v, i) => i > 0 && v < froms[i - 1]);
  let html = '<div class="justification-note mb-1">Extracted execution sequence '
    + (reordered
        ? '<span class="badge badge-low">re-sequenced vs. manual order</span>'
        : '<span class="badge badge-success">same order as manual steps</span>')
    + ' — the <b>from</b> column shows which refined step above each row came from:</div>';
  html += ' <span class="justification-note">Drag ⠿ to reorder.</span>';
  html += '<table class="table"><thead><tr><th style="width:20px"></th><th style="width:24px">#</th><th style="width:44px">from</th><th>Action</th><th>Verify</th><th style="width:30px"></th></tr></thead><tbody id="pt-seq-tbody">';
  seq.forEach((s, i) => {
    const from = (typeof s.zephyr_step_idx === 'number') ? s.zephyr_step_idx : '—';
    html += `<tr class="pt-seq-row" draggable="true" data-i="${i}">
      <td class="pt-seq-handle" title="Drag to reorder" style="cursor:grab;text-align:center;color:var(--text-muted)">⠿</td>
      <td>${i + 1}</td>
      <td style="text-align:center;font-size:11px" title="source refined step #">${from}</td>
      <td><textarea class="form-input pt-seq-action" data-i="${i}" style="width:100%;height:44px;font-size:11px">${escapeHtml(s.action || '')}</textarea></td>
      <td><textarea class="form-input pt-seq-verify" data-i="${i}" style="width:100%;height:44px;font-size:11px">${escapeHtml(s.verify || '')}</textarea></td>
      <td><button class="btn btn-compact" data-action="ptRemoveSeqRow" data-args='[${i}]'>✕</button></td>
    </tr>`;
  });
  html += '</tbody></table><button class="btn btn-compact mt-2" data-action="ptAddSeqRow">+ Add step</button>';
  el.innerHTML = html;
  ptWireSeqDrag();
}

// The `from` (zephyr_step_idx) is now display-only, so we cache it per-row alongside
// the live editable action/verify. ptCollectSequence reads the DOM order (which drag
// reorders), pairs each row with its cached from-index, and renumbers n.
let _ptSeqCache = [];   // parallel to render order: [{zephyr_step_idx?}]

function ptRenderSequenceCached(seq) {
  _ptSeqCache = seq.map(s => ({
    zephyr_step_idx: (typeof s.zephyr_step_idx === 'number') ? s.zephyr_step_idx : undefined,
  }));
  ptRenderSequence(seq);
}

// Read every row in DOM order (no filtering), pairing live action/verify edits with the
// cached display-only from-index. data-i equals the render position, so it indexes
// _ptSeqCache directly. Used by the render/drag/add/remove round-trips where row-to-row
// correspondence must be preserved.
function _ptReadSeqRows() {
  const rows = Array.from(document.querySelectorAll('#pt-seq-tbody .pt-seq-row'));
  return rows.map((row, i) => {
    const a = row.querySelector('.pt-seq-action');
    const v = row.querySelector('.pt-seq-verify');
    const from = _ptSeqCache[Number(row.dataset.i)] || {};
    const out = {
      n: i + 1,
      action: a ? a.value.trim() : '',
      verify: v && v.value ? v.value.trim() : '',
    };
    if (typeof from.zephyr_step_idx === 'number') out.zephyr_step_idx = from.zephyr_step_idx;
    return out;
  });
}

// Save/confirm collector: same as above but drops blank rows.
function ptCollectSequence() {
  return _ptReadSeqRows().filter(s => s.action);
}

// Native HTML5 drag-and-drop reorder. On drop we collect the (now reordered) sequence
// and re-render so #, the order badge, and the drag wiring all refresh.
let _ptDragSrc = null;
function ptWireSeqDrag() {
  const tbody = document.getElementById('pt-seq-tbody');
  if (!tbody) return;
  tbody.querySelectorAll('.pt-seq-row').forEach(row => {
    row.addEventListener('dragstart', e => {
      _ptDragSrc = row;
      row.style.opacity = '0.4';
      e.dataTransfer.effectAllowed = 'move';
    });
    row.addEventListener('dragend', () => {
      row.style.opacity = '';
      tbody.querySelectorAll('.pt-seq-row').forEach(r => r.classList.remove('pt-seq-drop-over'));
    });
    row.addEventListener('dragover', e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      if (row !== _ptDragSrc) row.classList.add('pt-seq-drop-over');
    });
    row.addEventListener('dragleave', () => row.classList.remove('pt-seq-drop-over'));
    row.addEventListener('drop', e => {
      e.preventDefault();
      if (!_ptDragSrc || row === _ptDragSrc) return;
      // Positions in the CURRENT render order (data-i is the render index here, so it
      // matches ptCollectSequence's output order and _ptSeqCache indexing).
      const from = Number(_ptDragSrc.dataset.i);
      const to = Number(row.dataset.i);
      const seq = _ptReadSeqRows();   // live edits + resolved from-indices, in render order (unfiltered)
      if (from >= seq.length || to >= seq.length) return;
      const [moved] = seq.splice(from, 1);
      seq.splice(to, 0, moved);
      ptRenderSequenceCached(seq);
    });
  });
}

function ptAddSeqRow() {
  const seq = _ptReadSeqRows();
  seq.push({ n: seq.length + 1, action: '', verify: '' });
  ptRenderSequenceCached(seq);
}

function ptRemoveSeqRow(i) {
  const seq = _ptReadSeqRows();
  seq.splice(i, 1);
  ptRenderSequenceCached(seq);
}

async function ptExtractSequence() {
  if (!ptRequireCase()) return;
  const btn = document.getElementById('pt-seq-extract-btn');
  const d = await ptApi(`/extract_sequence/${S.ptCase.key}`,
    { method: 'POST', btn, busyLabel: 'Extracting…' }, ptStatusEl('pt-seq-status'));
  recordLLMDebug(btn);
  if (!d) return;
  await ptRefreshSession();
  ptRenderSequenceCached(d.sequence || []);
  if (d.notes) ptStatusEl('pt-seq-status').textContent = 'LLM notes: ' + d.notes;
}

async function ptSaveSequence() {
  if (!ptRequireCase()) return;
  const seq = ptCollectSequence();
  if (!seq.length) { alert('Sequence is empty.'); return; }
  const d = await ptApi(`/save_sequence/${S.ptCase.key}`, {
    method: 'POST', body: JSON.stringify({ sequence: seq }),
  }, ptStatusEl('pt-seq-status'));
  if (d) { await ptRefreshSession(); ptStatusEl('pt-seq-status').textContent = 'Saved.'; }
}

// --- Step 3: Script Search (per-step picker) --------------------------------
//
// Script selection is done PER SEQUENCE STEP so it's obvious every step is covered.
// The global "Suggest from Sequence (LLM)" runs once and fans each match out under
// the step(s) named in its covers_steps. Each step section also has its own LLM
// Suggest and keyword search (results are linked to THAT step by construction). The
// reviewer chooses per step; selections persist as a {stepN: [ids]} map (save_matches),
// which downstream flattens. Every step shows a ✓ covered / ✗ gap status.
const PT_DBS = [
  { key: 'art', label: 'testsuites_art' },
  { key: 'svt', label: 'svt_scripts' },
  { key: 'legacy', label: 'test_scripts' },
];
let _ptStepCands = {};   // { stepN: [match record, ...] } — candidate pool per step
let _ptStepChosen = {};  // { stepN: [id, ...] } — chosen per step (source of truth)
let _ptRecCache = {};    // { id: record } — so chosen rows render after a re-search
let _ptCurStep = 0;      // 0-based index into the sequence — the one step shown (page-within-a-page)

function _ptSeq() { return ((ptSession || {}).step2 || {}).sequence || []; }
function _ptCacheRecs(recs) { (recs || []).forEach(m => { if (m && m.id) _ptRecCache[m.id] = { ..._ptRecCache[m.id], ...m }; }); }

// Enter in a per-step keyword box triggers that step's search. Delegated + bound once,
// so it survives the frequent re-renders of #pt-steps-list.
let _ptStepSearchBound = false;
function _ptBindStepSearch() {
  if (_ptStepSearchBound) return;
  const el = document.getElementById('pt-steps-list');
  if (!el) return;
  el.addEventListener('keydown', (e) => {
    const t = e.target;
    if (t && t.classList && t.classList.contains('pt-step-q') && e.key === 'Enter') {
      e.preventDefault();
      ptSearchStep(Number(t.getAttribute('data-step')));
    }
  });
  _ptStepSearchBound = true;
}

// Seed per-step candidate pools from the persisted global matches (fanned out by
// covers_steps) and restore chosen per step from the saved map. Does NOT touch
// _ptCurStep — callers decide whether to reset the viewer position.
function _ptSeedFromSession() {
  const st3 = (ptSession || {}).step3 || {};
  _ptStepCands = {};
  _ptRecCache = {};
  _ptSeq().forEach(s => { _ptStepCands[s.n] = []; });
  (st3.matches || []).forEach(m => {
    _ptCacheRecs([m]);
    (m.covers_steps || []).forEach(n => {
      if (!_ptStepCands[n]) _ptStepCands[n] = [];
      if (!_ptStepCands[n].some(x => x.id === m.id)) _ptStepCands[n].push(m);
    });
  });
  _ptStepChosen = {};
  const savedSel = st3.selections || {};
  if (savedSel && !Array.isArray(savedSel)) {
    Object.keys(savedSel).forEach(n => { _ptStepChosen[n] = (savedSel[n] || []).slice(); });
  } else if (Array.isArray(savedSel)) {
    // Legacy flat list: attach to whichever step the matching record covers, else step 1.
    savedSel.forEach(id => {
      const rec = _ptRecCache[id];
      const steps = (rec && rec.covers_steps && rec.covers_steps.length) ? rec.covers_steps : [(_ptSeq()[0] || {}).n || 1];
      steps.forEach(n => { (_ptStepChosen[n] = _ptStepChosen[n] || []).push(id); });
    });
  }
}

export function renderPtSearchPanel() {
  const el = document.getElementById('pt-steps-list');
  if (!ptSession) { if (el) el.innerHTML = '<em class="review-empty">Load a case first.</em>'; return; }
  const st3 = ptSession.step3 || {};
  _ptSeedFromSession();
  _ptCurStep = 0;                    // entering the panel starts at the first step
  ptRenderSteps();
  _ptBindStepSearch();
  mountPtProvenance('pt-match-prov', 'panel-pt-search', '/api/pytest-create/suggest_scripts/{key}', st3.provenance);
  updatePtBadges();
}

function _ptMatchTable(rows, stepN, kind) {
  if (!rows.length) {
    return kind === 'chosen'
      ? '<em class="chosen-empty">Nothing chosen for this step yet.</em>'
      : '<em class="review-empty">No candidates yet — Suggest or search below.</em>';
  }
  const { byDb, order } = (() => {
    const byDb = {};
    rows.forEach(m => { (byDb[m.db || 'other'] = byDb[m.db || 'other'] || []).push(m); });
    const order = PT_DBS.slice();
    Object.keys(byDb).forEach(k => { if (!order.some(d => d.key === k)) order.push({ key: k, label: k }); });
    return { byDb, order };
  })();
  const cbClass = kind === 'chosen' ? 'pt-chosen-sel' : 'pt-cand-sel';
  let html = '';
  order.forEach(({ key, label }) => {
    const group = byDb[key] || [];
    if (!group.length) return;
    html += `<div class="pt-match-db"><div class="pt-match-db-head">${escapeHtml(label)} <span class="justification-note">(${group.length})</span></div>`;
    html += '<div class="pt-match-scroll"><table class="table pt-match-table"><thead><tr><th></th><th>Script</th><th>Cov</th><th>Why</th><th></th></tr></thead><tbody>';
    group.forEach(m => {
      const cov = m.coverage || '?';
      const covClass = cov === 'full' ? 'badge-success' : (cov === 'partial' ? 'badge-low' : '');
      html += `<tr>
        <td><input type="checkbox" class="${cbClass}" data-step="${stepN}" value="${escapeHtml(m.id)}"></td>
        <td class="cell-id">${escapeHtml(m.id)}<div class="justification-note">${escapeHtml(m.title || '')}</div></td>
        <td><span class="badge ${covClass}">${escapeHtml(cov)}</span></td>
        <td class="justification-note">${escapeHtml(m.reason || '')}</td>
        <td><button class="btn btn-compact" data-action="ptViewSource" data-args="${dataArgs(m.id)}">view</button></td>
      </tr>`;
    });
    html += '</tbody></table></div></div>';
  });
  return html;
}

// Page-within-a-page: a coverage/nav bar + ONE step's picker at a time. Prev/Next
// and the per-step pills move _ptCurStep; only that step renders below.
function ptRenderSteps() {
  const el = document.getElementById('pt-steps-list');
  if (!el) return;
  const seq = _ptSeq();
  const sumEl = document.getElementById('pt-coverage-summary');
  if (!seq.length) {
    el.innerHTML = '<em class="review-empty">No sequence — confirm step 2 first.</em>';
    if (sumEl) sumEl.innerHTML = '';
    return;
  }
  if (_ptCurStep < 0) _ptCurStep = 0;
  if (_ptCurStep > seq.length - 1) _ptCurStep = seq.length - 1;

  const covered = seq.filter(s => (_ptStepChosen[s.n] || []).length).length;
  const gaps = seq.length - covered;

  // Nav / coverage bar: overall tally + Prev/Next + clickable per-step pills.
  if (sumEl) {
    const pills = seq.map((s, i) => {
      const ok = (_ptStepChosen[s.n] || []).length > 0;
      const cur = i === _ptCurStep ? ' pt-pill-current' : '';
      return `<button class="pt-pill ${ok ? 'pt-pill-ok' : 'pt-pill-gap'}${cur}" `
        + `data-action="ptGoStep" data-args='[${i}]' title="Step ${s.n}${ok ? ' — covered' : ' — no script yet'}">`
        + `${ok ? '✓' : '✗'} ${s.n}</button>`;
    }).join('');
    sumEl.innerHTML = `<div class="pt-stepnav">
      <span class="badge ${gaps ? 'badge-low' : 'badge-success'}">${covered}/${seq.length} steps covered${gaps ? ` — ${gaps} gap${gaps > 1 ? 's' : ''}` : ' ✓'}</span>
      <div class="pt-stepnav-btns">
        <button class="btn btn-compact" data-action="ptPrevStep" ${_ptCurStep === 0 ? 'disabled' : ''}>‹ Prev</button>
        <span class="pt-stepnav-pos">Step ${_ptCurStep + 1} of ${seq.length}</span>
        <button class="btn btn-compact" data-action="ptNextStep" ${_ptCurStep === seq.length - 1 ? 'disabled' : ''}>Next ›</button>
      </div>
      <div class="pt-pill-row">${pills}</div>
    </div>`;
  }

  // The single current step.
  const s = seq[_ptCurStep];
  const n = s.n;
  const chosenIds = new Set(_ptStepChosen[n] || []);
  const cands = (_ptStepCands[n] || []).filter(m => !chosenIds.has(m.id));
  const chosenRecs = (_ptStepChosen[n] || []).map(id => _ptRecCache[id] || { id, title: '', db: 'other', coverage: '?' });
  const ok = chosenIds.size > 0;
  el.innerHTML = `<div class="pt-step-block">
      <div class="pt-step-head">
        <span class="badge ${ok ? 'badge-success' : 'badge-low'}">${ok ? '✓' : '✗'}</span>
        <b>Step ${n}</b> — ${escapeHtml(s.action || '')}
        <span class="justification-note">${ok ? `${chosenIds.size} chosen` : 'no script yet'}</span>
      </div>
      <div class="justification-note pt-step-verify">verify: ${escapeHtml(s.verify || '')}</div>

      <div class="compact-flex mt-1 mb-2">
        <button class="btn btn-primary btn-compact" data-action="ptSuggestStep" data-args='[${n}]' id="pt-suggest-step-${n}">Suggest for step ${n} (LLM)</button>
        <input type="text" class="form-input form-input-search pt-step-q" data-step="${n}" placeholder="keyword search this step…">
        <button class="btn btn-compact" data-action="ptSearchStep" data-args='[${n}]'>Search</button>
        <span class="justification-note" id="pt-step-status-${n}"></span>
      </div>

      <div class="pt-step-sub">Candidates <span class="justification-note">— tick rows and Choose to shortlist them for this step</span></div>
      ${_ptMatchTable(cands, n, 'cand')}
      <div class="compact-flex mt-1 mb-2">
        <button class="btn btn-compact" data-action="ptChooseMatches" data-args='[${n}]'>↓ Choose ticked for step ${n}</button>
      </div>

      <div class="pt-step-sub">Chosen for this step <span class="justification-note">— reused for step ${n}; tick and Remove to move back up</span></div>
      ${_ptMatchTable(chosenRecs, n, 'chosen')}
      <div class="compact-flex mt-1">
        <button class="btn btn-compact" data-action="ptClearChosen" data-args='[${n}]'>↑ Remove ticked from step</button>
      </div>
      <div id="pt-source-view" class="mt-2"></div>
    </div>`;
}

function ptGoStep(i) { _ptCurStep = i; ptRenderSteps(); }
function ptPrevStep() { if (_ptCurStep > 0) { _ptCurStep -= 1; ptRenderSteps(); } }
function ptNextStep() { const seq = _ptSeq(); if (_ptCurStep < seq.length - 1) { _ptCurStep += 1; ptRenderSteps(); } }

function _ptAddCands(stepN, recs) {
  _ptCacheRecs(recs);
  const pool = _ptStepCands[stepN] = _ptStepCands[stepN] || [];
  recs.forEach(m => { if (m && m.id && !pool.some(x => x.id === m.id)) pool.push(m); });
}

// Choose ticked candidate rows for a step.
function ptChooseMatches(stepN) {
  const boxes = Array.from(document.querySelectorAll(`.pt-cand-sel[data-step="${stepN}"]:checked`));
  if (!boxes.length) { alert('Tick one or more candidate rows for this step first.'); return; }
  const chosen = _ptStepChosen[stepN] = _ptStepChosen[stepN] || [];
  boxes.forEach(cb => { if (!chosen.includes(cb.value)) chosen.push(cb.value); });
  ptRenderSteps();
}

// Remove ticked chosen rows from a step (they reappear as candidates if still pooled).
function ptClearChosen(stepN) {
  const boxes = Array.from(document.querySelectorAll(`.pt-chosen-sel[data-step="${stepN}"]:checked`));
  if (!boxes.length) { alert('Tick one or more chosen rows for this step first.'); return; }
  const remove = new Set(boxes.map(cb => cb.value));
  _ptStepChosen[stepN] = (_ptStepChosen[stepN] || []).filter(id => !remove.has(id));
  ptRenderSteps();
}

// Per-step LLM suggest — links every result to this step.
async function ptSuggestStep(stepN) {
  if (!ptRequireCase()) return;
  const btn = document.getElementById(`pt-suggest-step-${stepN}`);
  const st = document.getElementById(`pt-step-status-${stepN}`);
  const d = await ptApi(`/suggest_scripts_step/${S.ptCase.key}/${stepN}`, {
    method: 'POST',
    body: JSON.stringify({ user_inputs: '' }),
    btn, busyLabel: 'Suggesting…',
  }, st);
  recordLLMDebug(btn);
  if (!d) return;
  _ptAddCands(stepN, d.matches || []);
  ptRenderSteps();
  const el = document.getElementById(`pt-step-status-${stepN}`);
  if (el) el.textContent = `${(d.matches || []).length} match(es) for step ${stepN}.`;
}

// Per-step keyword search — links every result to this step.
async function ptSearchStep(stepN) {
  const input = document.querySelector(`.pt-step-q[data-step="${stepN}"]`);
  const q = input ? input.value.trim() : '';
  if (!q) return;
  const st = document.getElementById(`pt-step-status-${stepN}`);
  const d = await ptApi(`/search_scripts?q=${encodeURIComponent(q)}&limit=25`, {}, st);
  if (!d) return;
  const recs = (d.results || []).map(r => ({ ...r, coverage: r.coverage || 'partial', covers_steps: [stepN] }));
  _ptAddCands(stepN, recs);
  ptRenderSteps();
  const el = document.getElementById(`pt-step-status-${stepN}`);
  if (el) el.textContent = `${recs.length} hit(s) for "${q}" — linked to step ${stepN}.`;
}

async function ptSaveMatches() {
  if (!ptRequireCase()) return;
  const sel = {};
  Object.keys(_ptStepChosen).forEach(n => { if ((_ptStepChosen[n] || []).length) sel[n] = _ptStepChosen[n].slice(); });
  const total = new Set(Object.values(sel).flat()).size;
  const d = await ptApi(`/save_matches/${S.ptCase.key}`, {
    method: 'POST',
    body: JSON.stringify({ selections: sel }),
  }, ptStatusEl('pt-search-status'));
  if (d) { await ptRefreshSession(); ptStatusEl('pt-search-status').textContent = `Saved — ${total} unique script(s) across ${Object.keys(sel).length} step(s).`; }
}

async function ptViewSource(id) {
  const d = await ptApi(`/script_source?id=${encodeURIComponent(id)}&start=1&end=120`);
  if (!d) return;
  document.getElementById('pt-source-view').innerHTML =
    `<div class="justification-note">${escapeHtml(id)} (lines 1-120)</div><pre class="session-pre" style="max-height:300px;overflow:auto">${escapeHtml(d.source)}</pre>`;
}

// Step 4 (Fit Decision) was RETIRED — see routers/pytest_create.py. Fragments (below)
// now gather straight from the confirmed step-3 script selections; there is no
// reuse/extend/new panel anymore.

// --- Step 5 (shown as "4. Fragments"): per-step fragment picker ---------------
//
// Mirrors Step 3's page-within-a-page: one sequence step at a time, each with a
// "Not selected" and a "Selected" table. Gathered fragments fan out under every step
// in their maps_to (a multi-step fragment shows under each). Selection is by fragment
// identity (source_id+symbol) so it's consistent across the steps it appears in.
// Only SELECTED fragments feed Generate (backend _selected_fragments).
let _ptFragPool = [];      // full gathered pool (step5.fragments)
let _ptFragSel = new Set();// selected fragment keys "source_id||symbol"
let _ptFragStep = 0;       // 0-based index into the sequence (viewer position)
let _ptFragAcct = {};      // step5.accounting: {stepN: [{chosen:[sid,sym], redundant:[{key,why}]}]}
let _ptFragByKey = {};     // key -> pool fragment record (code/why/maps_to)

function _fragKey(f) { return `${f.source_id}||${f.symbol}`; }
function _keyOf(arr) { return `${arr[0]}||${arr[1]}`; }   // [sid,sym] -> "sid||sym"

function _ptFragSeedFromSession() {
  const s5 = (ptSession || {}).step5 || {};
  _ptFragPool = (s5.fragments || []).slice();
  _ptFragByKey = {};
  _ptFragPool.forEach(f => { _ptFragByKey[_fragKey(f)] = f; });
  _ptFragAcct = s5.accounting || {};
  if (s5.selected) {
    _ptFragSel = new Set((s5.selected || []).map(s => `${s.source_id}||${s.symbol}`));
  } else {
    // No explicit selection persisted yet → everything gathered is selected by default.
    _ptFragSel = new Set(_ptFragPool.map(_fragKey));
  }
}

// Fingerprint of the CURRENT step-3 script selections (must match the backend's
// _selections_fingerprint: order-independent, de-duped, '|'-joined ids).
function _ptCurrentSelFingerprint() {
  const sel = ((ptSession || {}).step3 || {}).selections;
  const ids = new Set();
  if (sel && !Array.isArray(sel)) { Object.values(sel).forEach(a => (a || []).forEach(id => ids.add(id))); }
  else if (Array.isArray(sel)) { sel.forEach(id => ids.add(id)); }
  return Array.from(ids).sort().join('|');
}

// Fragments are stale if Step 3's selections changed since they were gathered.
function _ptFragsStale() {
  const s5 = (ptSession || {}).step5 || {};
  if (!(_ptFragPool.length)) return false;                 // nothing gathered → nothing stale
  if (s5.selections_fingerprint == null) return true;      // pre-fingerprint gather → treat as stale
  return s5.selections_fingerprint !== _ptCurrentSelFingerprint();
}

export function renderPtFragPanel() {
  const el = document.getElementById('pt-frag-list');
  if (!ptSession) { if (el) el.innerHTML = '<em class="review-empty">Load a case first.</em>'; return; }
  _ptFragSeedFromSession();
  _ptFragStep = 0;
  ptRenderFragSteps();
  _ptBindFragUI();
  mountPtProvenance('pt-frag-prov', 'panel-pt-frag', '/api/pytest-create/gather_fragments/{key}', (ptSession.step5 || {}).provenance);
  updatePtBadges();
}

// Fragments that map to a given step number (multi-step frags appear under each).
function _fragsForStep(n) {
  return _ptFragPool.filter(f => (f.maps_to || []).map(Number).includes(n));
}

// Render one fragment card: green-outlined if chosen, faint-red if a redundant nest.
// The checkbox directly toggles selection (ptFragToggle). `redundantWhy` is set for
// nested redundant fragments (their reason they duplicate the chosen one).
function _fragCard(key, opts) {
  opts = opts || {};
  const f = _ptFragByKey[key];
  if (!f) return '';
  const selected = _ptFragSel.has(key);
  const lines = (f.code || '').split('\n').length;
  const cls = opts.redundant ? 'pt-frag-card pt-frag-redundant' : 'pt-frag-card pt-frag-chosen';
  const why = opts.redundantWhy != null ? opts.redundantWhy : (f.why || '');
  const whyLabel = opts.redundant ? 'redundant:' : '';
  return `<div class="${cls}${selected ? ' is-selected' : ''}">
    <label class="pt-frag-card-head">
      <input type="checkbox" class="pt-frag-toggle" data-args='["${escapeHtml(key)}"]' data-action="ptFragToggle" ${selected ? 'checked' : ''}>
      <b>${escapeHtml(f.symbol)}</b>
      <span class="justification-note">from ${escapeHtml(f.source_id)} · steps ${(f.maps_to || []).join(', ')}</span>
    </label>
    <div class="justification-note pt-frag-why">${whyLabel ? `<b>${whyLabel}</b> ` : ''}${escapeHtml(why)}</div>
    <details><summary class="justification-note">code (${lines} lines)</summary>
      <pre class="session-pre" style="max-height:220px;overflow:auto">${escapeHtml(f.code || '')}</pre></details>
  </div>`;
}

function ptRenderFragSteps() {
  const el = document.getElementById('pt-frag-list');
  const sumEl = document.getElementById('pt-frag-coverage');
  if (!el) return;
  const seq = _ptSeq();
  const staleBanner = _ptFragsStale()
    ? `<div class="pt-frag-stale">⚠ Script selections changed in <b>3. Script Search</b> since these fragments were gathered — they may be out of date. Re-run <b>Gather Fragments (LLM)</b> to refresh from your current selection.</div>`
    : '';
  if (!_ptFragPool.length) {
    el.innerHTML = '<em class="review-empty">No fragments yet — run Gather Fragments (LLM). (A "new script from scratch" plan may legitimately keep this empty — Save then Confirm.)</em>';
    if (sumEl) sumEl.innerHTML = staleBanner;
    return;
  }
  if (!seq.length) { el.innerHTML = '<em class="review-empty">No sequence — confirm step 2 first.</em>'; return; }
  if (_ptFragStep < 0) _ptFragStep = 0;
  if (_ptFragStep > seq.length - 1) _ptFragStep = seq.length - 1;

  // A step is "covered" if at least one SELECTED fragment maps to it.
  const stepHasSel = (n) => _fragsForStep(n).some(f => _ptFragSel.has(_fragKey(f)));
  const covered = seq.filter(s => stepHasSel(s.n)).length;
  const gaps = seq.length - covered;
  if (sumEl) {
    const pills = seq.map((s, i) => {
      const ok = stepHasSel(s.n);
      const cur = i === _ptFragStep ? ' pt-pill-current' : '';
      return `<button class="pt-pill ${ok ? 'pt-pill-ok' : 'pt-pill-gap'}${cur}" data-action="ptFragGoStep" data-args='[${i}]' title="Step ${s.n}${ok ? ' — has a selected fragment' : ' — none selected'}">${ok ? '✓' : '✗'} ${s.n}</button>`;
    }).join('');
    sumEl.innerHTML = staleBanner + `<div class="pt-stepnav">
      <span class="badge ${gaps ? 'badge-low' : 'badge-success'}">${covered}/${seq.length} steps with a selected fragment${gaps ? ` — ${gaps} gap${gaps > 1 ? 's' : ''}` : ' ✓'}</span>
      <div class="pt-stepnav-btns">
        <button class="btn btn-compact" data-action="ptFragPrevStep" ${_ptFragStep === 0 ? 'disabled' : ''}>‹ Prev</button>
        <span class="pt-stepnav-pos">Step ${_ptFragStep + 1} of ${seq.length}</span>
        <button class="btn btn-compact" data-action="ptFragNextStep" ${_ptFragStep === seq.length - 1 ? 'disabled' : ''}>Next ›</button>
      </div>
      <div class="pt-pill-row">${pills}</div>
    </div>`;
  }

  const s = seq[_ptFragStep];
  const n = s.n;
  const selCount = _fragsForStep(n).filter(f => _ptFragSel.has(_fragKey(f))).length;
  const ok = selCount > 0;

  // Accounting entries for this step: each chosen fragment + its redundant nest.
  const entries = _ptFragAcct[String(n)] || [];
  let body = '';
  const shown = new Set();
  if (entries.length) {
    entries.forEach(en => {
      const ck = _keyOf(en.chosen);
      shown.add(ck);
      body += _fragCard(ck, { redundant: false });
      const reds = en.redundant || [];
      if (reds.length) {
        body += '<div class="pt-frag-redundant-wrap"><div class="pt-frag-redundant-label">Not selected — redundant to the above:</div>';
        reds.forEach(r => {
          const rk = _keyOf(r.key);
          shown.add(rk);
          body += _fragCard(rk, { redundant: true, redundantWhy: r.why });
        });
        body += '</div>';
      }
    });
  }
  // Any fragment mapping to this step that the accounting didn't place (legacy/stale
  // gathers with no accounting, or manually-relevant frags) — show plainly.
  const leftovers = _fragsForStep(n).filter(f => !shown.has(_fragKey(f)));
  if (leftovers.length) {
    if (entries.length) body += '<div class="pt-frag-redundant-label mt-2">Other fragments serving this step:</div>';
    leftovers.forEach(f => { body += _fragCard(_fragKey(f), { redundant: false }); });
  }
  if (!body) body = '<em class="review-empty">No fragment covers this step — genuine gap (Generate will fill it).</em>';

  el.innerHTML = `<div class="pt-step-block">
      <div class="pt-step-head">
        <span class="badge ${ok ? 'badge-success' : 'badge-low'}">${ok ? '✓' : '✗'}</span>
        <b>Step ${n}</b> — ${escapeHtml(s.action || '')}
        <span class="justification-note">${ok ? `${selCount} selected` : 'no fragment selected'}</span>
      </div>
      <div class="justification-note pt-step-verify">verify: ${escapeHtml(s.verify || '')}</div>
      <div class="justification-note mb-2">Tick a fragment's box to include its code in Generate. Green = chosen by the LLM; red = a redundant alternative it was preferred over (tick it to override).</div>
      ${body}
    </div>`;
}

function ptFragGoStep(i) { _ptFragStep = i; ptRenderFragSteps(); }
function ptFragPrevStep() { if (_ptFragStep > 0) { _ptFragStep -= 1; ptRenderFragSteps(); } }
function ptFragNextStep() { const seq = _ptSeq(); if (_ptFragStep < seq.length - 1) { _ptFragStep += 1; ptRenderFragSteps(); } }

// Toggle one fragment's selection (drives what Generate uses). `this` is the checkbox.
function ptFragToggle(key) {
  if (this && this.checked) _ptFragSel.add(key); else _ptFragSel.delete(key);
  ptRenderFragSteps();
}

// Current selection as a keep list for preview/save.
function _ptFragKeepList() {
  return _ptFragPool.filter(f => _ptFragSel.has(_fragKey(f)))
    .map(f => ({ source_id: f.source_id, symbol: f.symbol }));
}

// Assemble + show the per-step artefact (skeleton + selected-fragment code slotted in),
// reflecting the LIVE selection (unsaved toggles included).
async function ptPreviewFragments() {
  if (!ptRequireCase()) return;
  const btn = document.getElementById('pt-frag-preview-btn');
  const codeEl = document.getElementById('pt-frag-preview-code');
  const st = document.getElementById('pt-frag-preview-status');
  const d = await ptApi(`/preview_fragments/${S.ptCase.key}`, {
    method: 'POST', body: JSON.stringify({ keep: _ptFragKeepList() }),
    btn, busyLabel: 'Assembling…',
  }, st);
  if (!d) return;
  if (codeEl) codeEl.textContent = d.preview || '(empty)';
  if (st) st.textContent = `${d.selected_count} selected fragment(s) slotted into the skeleton.`;
}

let _ptFragUIBound = false;
function _ptBindFragUI() { _ptFragUIBound = true; /* reserved for future delegated handlers */ }

async function ptGatherFragments() {
  if (!ptRequireCase()) return;
  const btn = document.getElementById('pt-frag-btn');
  const d = await ptApi(`/gather_fragments/${S.ptCase.key}`,
    { method: 'POST', btn, busyLabel: 'Gathering…' }, ptStatusEl('pt-frag-status'));
  recordLLMDebug(btn);
  if (!d) return;
  await ptRefreshSession();
  _ptFragSeedFromSession();          // merge new pool + selections, keep viewer position
  ptRenderFragSteps();
  const bits = [];
  if (d.scripts_considered != null) bits.push(`from ${d.scripts_considered} selected script(s)`);
  if (d.added != null) bits.push(`${d.added} new fragment(s) added`);
  if (d.dropped) bits.push(`${d.dropped} proposed fragment(s) failed symbol resolution and were dropped`);
  if (bits.length) ptStatusEl('pt-frag-status').textContent = bits.join(' · ') + '.';
}

async function ptSaveFragments() {
  if (!ptRequireCase()) return;
  const keep = _ptFragPool.filter(f => _ptFragSel.has(_fragKey(f)))
    .map(f => ({ source_id: f.source_id, symbol: f.symbol }));
  const d = await ptApi(`/save_fragments/${S.ptCase.key}`, {
    method: 'POST', body: JSON.stringify({ keep }),
  }, ptStatusEl('pt-frag-status'));
  if (d) { await ptRefreshSession(); ptStatusEl('pt-frag-status').textContent = `Saved — ${keep.length} fragment(s) selected for generation.`; }
}

// --- Step 6: Generate ---------------------------------------------------------

function ptUpdateGenPath() {
  const g = document.getElementById('pt-gen-group').value.trim() || '<Group>';
  const n = document.getElementById('pt-gen-name').value.trim() || '<Name>';
  document.getElementById('pt-gen-path').textContent = `→ generated/${g}/${n}.py`;
}

export function renderPtGenPanel() {
  if (!ptSession) { ptStatusEl('pt-gen-status').textContent = 'Load a case first.'; return; }
  const s6 = ptSession.step6 || {};
  const naming = s6.naming || {};
  const groupEl = document.getElementById('pt-gen-group');
  const nameEl = document.getElementById('pt-gen-name');
  groupEl.value = naming.group || (ptCaseInfo ? ptCaseInfo.group_display : '');
  nameEl.value = naming.name || '';
  groupEl.oninput = ptUpdateGenPath;
  nameEl.oninput = ptUpdateGenPath;
  ptUpdateGenPath();
  const files = s6.files || {};
  document.getElementById('pt-gen-code').value = (files.test || {}).code || '';
  const lib = files.library;
  document.getElementById('pt-gen-lib-wrap').classList.toggle('hidden', !lib);
  if (lib) {
    document.getElementById('pt-gen-lib-name').textContent = lib.name || '';
    document.getElementById('pt-gen-lib-code').value = lib.code || '';
  }
  ptRenderLint(s6.lint);
  if (s6.iterations) ptStatusEl('pt-gen-status').textContent = `Iteration ${s6.iterations}.`;
  // Generate + Fix both write step6; the provenance block covers generate_script.
  // Fix reuses the same block via its own endpoint on Refresh from the Gen panel.
  mountPtProvenance('pt-gen-prov', 'panel-pt-gen', '/api/pytest-create/generate_script/{key}', s6.provenance);
  updatePtBadges();
}

function ptRenderLint(lint) {
  const el = document.getElementById('pt-lint-result');
  if (!lint) { el.innerHTML = ''; return; }
  const err = (lint.errors || []).map(e => `<div>✗ ${escapeHtml(e)}</div>`).join('');
  const warn = (lint.warnings || []).map(w => `<div>△ ${escapeHtml(w)}</div>`).join('');
  el.innerHTML = `<span class="badge ${lint.ok ? 'badge-success' : ''}">${lint.ok ? 'lint OK' : 'lint failed'}</span>`
    + `<div class="justification-note">${err}${warn}</div>`;
}

async function ptGenerateScript() {
  if (!ptRequireCase()) return;
  const btn = document.getElementById('pt-gen-btn');
  const d = await ptApi(`/generate_script/${S.ptCase.key}`, {
    method: 'POST',
    body: JSON.stringify({
      group: document.getElementById('pt-gen-group').value.trim(),
      name: document.getElementById('pt-gen-name').value.trim(),
    }),
    btn, busyLabel: 'Generating…',
  }, ptStatusEl('pt-gen-status'));
  recordLLMDebug(btn);
  if (!d) return;
  await ptRefreshSession();
  renderPtGenPanel();
}

async function ptLintScript() {
  if (!ptRequireCase()) return;
  // push current edits into the session first so lint sees them
  await ptPushCodeEdits(false);
  const d = await ptApi(`/lint_script/${S.ptCase.key}`, { method: 'POST' }, ptStatusEl('pt-gen-status'));
  if (d) ptRenderLint(d);
}

async function ptPushCodeEdits(writeFiles) {
  const body = {
    group: document.getElementById('pt-gen-group').value.trim(),
    name: document.getElementById('pt-gen-name').value.trim(),
    code: document.getElementById('pt-gen-code').value,
  };
  const libWrap = document.getElementById('pt-gen-lib-wrap');
  if (!libWrap.classList.contains('hidden')) {
    body.library_code = document.getElementById('pt-gen-lib-code').value;
  }
  if (!writeFiles) {
    // save_script both persists edits and writes files; for lint-only we still
    // use it (files on disk mirror the session) — acceptable per plan.
  }
  return await ptApi(`/save_script/${S.ptCase.key}`, {
    method: 'POST', body: JSON.stringify(body),
  }, ptStatusEl('pt-gen-status'));
}

async function ptSaveScript() {
  if (!ptRequireCase()) return;
  const d = await ptPushCodeEdits(true);
  if (!d) return;
  await ptRefreshSession();
  ptRenderLint(d.lint);
  ptStatusEl('pt-gen-status').textContent = 'Saved: ' + (d.written || []).join(', ');
}

// --- Step 7: Run ---------------------------------------------------------------

let ptProfiles = {};

async function ptLoadProfiles() {
  const d = await ptApi('/profiles');
  ptProfiles = (d && d.profiles) || {};
  return ptProfiles;
}

function ptProfileLabel(name, p) {
  return `${name} — ${p.tb_number || '?'} (${p.host || '?'})`;
}

export async function renderPtRunPanel() {
  await ptLoadProfiles();
  const sel = document.getElementById('pt-run-profile');
  const cur = ((ptSession || {}).step7 || {}).profile;
  sel.innerHTML = '<option value="">Select testbox…</option>'
    + Object.entries(ptProfiles).map(([n, p]) =>
      `<option value="${escapeHtml(n)}" ${n === cur ? 'selected' : ''}>${escapeHtml(ptProfileLabel(n, p))}</option>`).join('')
    + '<option value="__add__">➕ Add new testbox…</option>';
  ptProfileSelected(sel);
  ptRenderRuns();
  updatePtBadges();
}

export function ptProfileSelected(sel) {
  if (sel.value === '__add__') {
    sel.value = '';
    goToPanel('panel-pt-testbox');
    return;
  }
  const p = ptProfiles[sel.value];
  const setupSel = document.getElementById('pt-run-setup');
  setupSel.innerHTML = '';
  if (p && p.setups && Object.keys(p.setups).length) {
    setupSel.innerHTML = Object.entries(p.setups).map(([n, path]) =>
      `<option value="${escapeHtml(n)}">${escapeHtml(n)} (${escapeHtml(path)})</option>`).join('');
  } else {
    setupSel.innerHTML = '<option value="">— none stored —</option>';
  }
}

async function ptCheckProfile() {
  const name = document.getElementById('pt-run-profile').value;
  if (!name) { alert('Select a testbox first.'); return; }
  const st = ptStatusEl('pt-run-status');
  st.textContent = 'Checking…';
  const d = await ptApi(`/profiles/${encodeURIComponent(name)}/check`, { method: 'POST' }, st);
  if (d) st.textContent = (d.ok ? '✓ ready — ' : '✗ not ready — ') + (d.detail || JSON.stringify(d));
}

function ptRenderRuns() {
  const runs = ((ptSession || {}).step7 || {}).runs || [];
  const el = document.getElementById('pt-run-results');
  if (!runs.length) { el.innerHTML = '<em class="review-empty">No runs yet.</em>'; return; }
  const last = runs[runs.length - 1];
  let html = `<div class="mb-1"><b>Run ${escapeHtml(last.run_id)}</b> on ${escapeHtml(last.profile || '')} — `
    + `<span class="badge ${last.status === 'done' ? 'badge-success' : ''}">${escapeHtml(last.status)}</span>`
    + (last.error ? ` <span class="justification-note">⚠ ${escapeHtml(last.error)}</span>` : '') + '</div>';
  const parsed = last.parsed || {};
  if ((parsed.cases || []).length) {
    html += '<table class="table"><thead><tr><th>TestCase</th><th style="width:80px">Result</th><th>Failures</th></tr></thead><tbody>';
    parsed.cases.forEach(c => {
      html += `<tr><td class="cell-id">${escapeHtml(c.name)}</td>
        <td><span class="badge ${c.result === 'PASS' ? 'badge-success' : ''}">${escapeHtml(c.result || '?')}</span></td>
        <td class="justification-note">${(c.fail_msgs || []).map(escapeHtml).join('; ')}</td></tr>`;
    });
    html += `</tbody></table><div class="justification-note">numPassed ${parsed.numPassed || 0} · numFailed ${parsed.numFailed || 0}</div>`;
  }
  if (runs.length > 1) html += `<div class="justification-note mt-1">${runs.length - 1} earlier run(s) in session history.</div>`;
  el.innerHTML = html;
}

async function ptRun() {
  if (!ptRequireCase()) return;
  const profile = document.getElementById('pt-run-profile').value;
  if (!profile) { alert('Select a testbox.'); return; }
  const setupName = document.getElementById('pt-run-setup').value;
  const setupPath = document.getElementById('pt-run-setup-path').value.trim();
  const d = await ptApi(`/run/${S.ptCase.key}`, {
    method: 'POST',
    body: JSON.stringify({ profile, setup: setupPath || setupName }),
  }, ptStatusEl('pt-run-status'));
  if (!d) return;
  ptStatusEl('pt-run-status').textContent = `Run ${d.run_id} queued…`;
  if (ptRunPoll) clearInterval(ptRunPoll);
  ptRunPoll = setInterval(() => ptPollRun(d.run_id), 4000);
}

async function ptPollRun(runId) {
  const d = await ptApi(`/run_status/${S.ptCase.key}/${runId}?tail=60`);
  if (!d) { clearInterval(ptRunPoll); ptRunPoll = null; return; }
  await ptRefreshSession();
  ptRenderRuns();
  document.getElementById('pt-run-log').textContent = d.log_tail || '';
  ptStatusEl('pt-run-status').textContent = `Run ${runId}: ${d.run.status}`;
  if (['done', 'error', 'stale'].includes(d.run.status)) {
    clearInterval(ptRunPoll);
    ptRunPoll = null;
  }
}

// --- Step 8: Validate ------------------------------------------------------------

export function renderPtValidatePanel() {
  const el = document.getElementById('pt-validate-result');
  if (!ptSession) { el.innerHTML = '<em class="review-empty">Load a case first.</em>'; return; }
  const s8 = ptSession.step8 || {};
  if (!s8.checks) { el.innerHTML = '<em class="review-empty">Run Final Validation after a testbox run.</em>'; updatePtBadges(); return; }
  ptRenderValidation({ validated: s8.validated, checks: s8.checks, promotion: null });
  updatePtBadges();
}

function ptRenderValidation(d) {
  const el = document.getElementById('pt-validate-result');
  const rows = Object.entries(d.checks || {}).map(([k, v]) =>
    `<tr><td>${escapeHtml(k)}</td><td>${v ? '✓' : '✗'}</td></tr>`).join('');
  el.innerHTML = `<div class="mb-2"><span class="badge ${d.validated ? 'badge-success' : ''}">`
    + `${d.validated ? 'VALIDATED — all checks pass' : 'Not validated yet'}</span></div>`
    + `<table class="table" style="max-width:420px"><tbody>${rows}</tbody></table>`
    + (d.promotion ? `<div class="justification-note mt-2">${escapeHtml(d.promotion)}</div>` : '');
}

async function ptValidate() {
  if (!ptRequireCase()) return;
  const d = await ptApi(`/validate/${S.ptCase.key}`, { method: 'POST' }, ptStatusEl('pt-validate-status'));
  if (!d) return;
  await ptRefreshSession();
  ptRenderValidation(d);
}

async function ptFixScript() {
  if (!ptRequireCase()) return;
  const btn = document.getElementById('pt-fix-btn');
  const d = await ptApi(`/fix_script/${S.ptCase.key}`,
    { method: 'POST', btn, busyLabel: 'Fixing…' }, ptStatusEl('pt-validate-status'));
  // Awaited (unlike the other handlers): this handler navigates to panel-pt-gen
  // below, and the record must be filed under THIS panel before currentPanel changes.
  await recordLLMDebug(btn);
  if (!d) return;
  await ptRefreshSession();
  ptStatusEl('pt-validate-status').textContent =
    `Revised (iteration ${d.iterations}); previous code archived. Review in 6. Generate, then re-run.`;
  goToPanel('panel-pt-gen');
}

// --- Testboxes (profiles CRUD) -----------------------------------------------------

export async function renderPtTestboxPanel() {
  await ptLoadProfiles();
  const el = document.getElementById('pt-tb-list');
  const names = Object.keys(ptProfiles);
  if (!names.length) { el.innerHTML = '<em class="review-empty">No testboxes stored yet — add one below.</em>'; return; }
  let html = '<table class="table"><thead><tr><th>Name</th><th>tb</th><th>IP</th><th>User</th><th>Auth</th><th style="width:150px"></th></tr></thead><tbody>';
  names.forEach(n => {
    const p = ptProfiles[n];
    html += `<tr><td><b>${escapeHtml(n)}</b></td><td>${escapeHtml(p.tb_number || '')}</td>
      <td class="cell-id">${escapeHtml(p.host || '')}</td><td>${escapeHtml(p.user || '')}</td>
      <td>${escapeHtml(p.auth || '')}${p.has_password ? ' (pw set)' : ''}</td>
      <td>
        <button class="btn btn-compact" data-action="ptEditProfile" data-args="${dataArgs(n)}">edit</button>
        <button class="btn btn-compact" data-action="ptCheckProfileNamed" data-args="${dataArgs(n)}">check</button>
        <button class="btn btn-compact" data-action="ptDeleteProfile" data-args="${dataArgs(n)}">✕</button>
      </td></tr>`;
  });
  el.innerHTML = html + '</tbody></table>';
}

function ptEditProfile(name) {
  const p = ptProfiles[name];
  if (!p) return;
  document.getElementById('pt-tb-name').value = name;
  document.getElementById('pt-tb-number').value = p.tb_number || '';
  document.getElementById('pt-tb-host').value = p.host || '';
  document.getElementById('pt-tb-user').value = p.user || '';
  document.getElementById('pt-tb-auth').value = p.auth || 'key';
  document.getElementById('pt-tb-keypath').value = p.key_path || '';
  document.getElementById('pt-tb-password').value = '';
  document.getElementById('pt-tb-framework').value = p.framework_path || '';
  document.getElementById('pt-tb-workdir').value = p.remote_workdir || '';
  const setups = p.setups || {};
  document.getElementById('pt-tb-setup').value = setups.default || Object.values(setups)[0] || '';
}

async function ptSaveProfile() {
  const name = document.getElementById('pt-tb-name').value.trim();
  const body = {
    name,
    tb_number: document.getElementById('pt-tb-number').value.trim(),
    host: document.getElementById('pt-tb-host').value.trim(),
    user: document.getElementById('pt-tb-user').value.trim() || 'st-art',
    auth: document.getElementById('pt-tb-auth').value,
    key_path: document.getElementById('pt-tb-keypath').value.trim() || '~/.ssh/id_rsa',
    framework_path: document.getElementById('pt-tb-framework').value.trim() || '/home/st-art/framework',
    remote_workdir: document.getElementById('pt-tb-workdir').value.trim() || '/home/st-art/pytest-create',
  };
  const pw = document.getElementById('pt-tb-password').value;
  if (pw) body.password = pw;
  const setupPath = document.getElementById('pt-tb-setup').value.trim();
  if (setupPath) body.setups = { default: setupPath };
  const d = await ptApi('/profiles', { method: 'POST', body: JSON.stringify(body) }, ptStatusEl('pt-tb-status'));
  if (d) {
    document.getElementById('pt-tb-password').value = '';
    ptStatusEl('pt-tb-status').textContent = `Saved "${d.saved}".`;
    renderPtTestboxPanel();
  }
}

async function ptDeleteProfile(name) {
  if (!confirm(`Delete testbox "${name}"?`)) return;
  const d = await ptApi(`/profiles/${encodeURIComponent(name)}`, { method: 'DELETE' }, ptStatusEl('pt-tb-status'));
  if (d) renderPtTestboxPanel();
}

async function ptCheckProfileNamed(name) {
  const st = ptStatusEl('pt-tb-status');
  st.textContent = `Checking ${name}…`;
  const d = await ptApi(`/profiles/${encodeURIComponent(name)}/check`, { method: 'POST' }, st);
  if (d) st.textContent = `${name}: ` + (d.ok ? '✓ ready — ' : '✗ not ready — ') + (d.detail || '');
}


// Register this tool's data-action handlers.
registerActions({
  ptLoadCase, ptRefreshCases, ptExtractSequence,
  ptAddSeqRow, ptRemoveSeqRow, ptSaveSequence,
  ptConfirm, ptSuggestStep, ptSearchStep,
  ptChooseMatches, ptClearChosen,
  ptGoStep, ptPrevStep, ptNextStep,
  ptSaveMatches,
  ptGatherFragments, ptSaveFragments, ptGenerateScript,
  ptFragGoStep, ptFragPrevStep, ptFragNextStep, ptFragToggle, ptPreviewFragments,
  ptLintScript, ptFixScript, ptSaveScript,
  ptViewSource, ptRun, ptValidate,
  ptEditProfile, ptSaveProfile, ptCheckProfile,
  ptCheckProfileNamed, ptDeleteProfile,
});
