// PyTest Creator: the full 8-step gated flow.
import { registerActions } from './actions.js';
import { S } from './state.js';
import { dataArgs, escapeHtml, setButtonBusy, flashButtonDone } from './dom-helpers.js';
import { refreshCaseSelects } from './cases.js';
import { goToPanel } from './nav.js';
import { recordLLMDebug } from './llm-debug.js';
import { registerProvenance, renderProvenanceBlock, seedProvenanceFromStep } from './provenance.js';
import { onCaseLoaded, registerReloader } from './locks.js';
import { llmButtonStart, isCancelMessage, newCallId, cancelLlmCall } from './llm-progress.js';
import { rememberCase } from './session-restore.js';

// Let "Take over" (locks.js) re-run the editable load without a circular import.
registerReloader('pt', ptLoadCase);

// Mount the shared LLM Provenance block into a per-panel container, wired to the
// panel's endpoint (dry_run for Refresh). `stepProv` seeds the last real call's
// prompt/response from the session when present.
// `bodyFn` (optional) supplies the panel's LIVE inputs for the dry-run, exactly as
// provenance.js documents: "returns the request body (minus dry_run) at click time so it
// always reflects current naming/inputs". Every panel here used to pass nothing, so the
// hard-coded `() => ({})` sent an EMPTY body and the endpoint fell back to its server-side
// defaults -- Refresh rendered a prompt for state the reviewer could see was not what the
// page showed. On the Generate panel that was worse than misleading: the fallback group for
// AWPTCM-T33351 was 'Authentication & Security', which _validate_naming rejects, so Refresh
// 400'd with "Invalid group name" naming a group the reviewer had already edited away
// (2026-08-31). A real Generate never hit it -- ptGenerateScript posts the inputs.
function mountPtProvenance(mountId, panelId, endpoint, stepProv, bodyFn) {
  const mount = document.getElementById(mountId);
  if (!mount || !S.ptCase) return;
  // `endpoint` may be a function when the target depends on live state — step 3's
  // suggest is per SEQUENCE STEP, so the URL is only knowable at click time.
  const endpointFn = typeof endpoint === 'function'
    ? endpoint
    : () => endpoint.replace('{key}', encodeURIComponent(S.ptCase.key));
  registerProvenance(panelId, endpointFn, bodyFn || (() => ({})));
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
//   doneLabel — label held on the button during the success flash. Worth setting for
//               anything FAST: a save that answers in 80ms shows its spinner for one
//               frame, and a reviewer watching the button reports seeing nothing.
//   errRef    — {} that receives {msg} on failure INSTEAD of a blocking alert. Per-unit
//               generation needs this: `alert` freezes the event loop, so during a
//               concurrent fan-out every other unit's result queues behind the dialog.
// The busy guard also stops a second click from stacking a duplicate LLM call.
async function ptApi(path, opts = {}, statusEl = null) {
  const { btn = null, busyLabel, doneLabel, llm = false, errRef = null,
          ...fetchOpts } = opts;
  // llm:true = this call really sends tokens — the button becomes a live Stop
  // button with elapsed / typical / streamed progress (llm-progress.js).
  let llmCtl = null;
  if (btn && llm) {
    llmCtl = llmButtonStart(btn, busyLabel || 'Working…');
    if (!llmCtl) return null;                       // same double-click guard
  } else if (btn && !setButtonBusy(btn, true, { label: busyLabel || 'Working…' })) return null;
  if (statusEl) statusEl.textContent = 'Working…';
  let ok = false;
  try {
    const r = await fetch(PT_API + path, Object.assign({}, fetchOpts, {
      headers: Object.assign({ 'Content-Type': 'application/json' },
                             llmCtl ? llmCtl.headers : {}, fetchOpts.headers || {}),
    }));
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      const msg = d.detail || `HTTP ${r.status}`;
      // The user's own Stop is not a failure — say what happened, calmly.
      const shown = isCancelMessage(msg) ? '⏹ stopped — nothing was kept.' : '⚠ ' + msg;
      if (errRef) errRef.msg = msg;
      else if (statusEl) statusEl.textContent = shown;
      else alert('PyTest Creator: ' + msg);
      return null;
    }
    if (statusEl) statusEl.textContent = '';
    ok = true;
    return d;
  } catch (e) {
    if (errRef) errRef.msg = String(e);
    else if (statusEl) statusEl.textContent = '⚠ ' + e;
    else alert('PyTest Creator: ' + e);
    return null;
  } finally {
    const done = ok && doneLabel ? { label: doneLabel } : undefined;
    if (llmCtl) { llmCtl.end(); flashButtonDone(btn, ok, done); }
    else if (btn) { setButtonBusy(btn, false); flashButtonDone(btn, ok, done); }
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
    + 'A case appears here only once it has a refined zephyr_payload.json (export it in the Objective/Test Case Generator first); it moves to Complete once its PyTest script passes Final Validation (step 7).';
  if (btn) btn.disabled = false;
}

export async function ptLoadCase() {
  if (!S.ptCase.key) { alert('Select a case first (Open/Partial, or Complete to revisit one).'); return; }
  const st = ptStatusEl('pt-load-status');
  const d = await ptApi(`/load_case/${S.ptCase.key}`, { method: 'POST' }, st);
  if (!d) return;
  ptSession = d.session;
  ptCaseInfo = { title: d.case_title, group_display: d.group_display,
                 objective: d.objective, steps: d.steps };
  // Per-unit state belongs to ONE case. Without this, loading a second case leaves the
  // first case's units in memory — and renderPtGenPanel only re-fetches when the list is
  // empty, so the pills, the prompts and the returned code would all be the previous
  // case's while the panel header says this one. Found by the jsdom spec (2026-09-02).
  _ptStopUnitPoll();
  _ptUnits = [];
  _ptUnitIdx = 0;
  _ptUnitSending = {};
  _ptUnitFails = [];
  rememberCase('pt', S.ptCase.key, true);   // survives a refresh (session-restore.js)
  updatePtBadges();
  // Per-case lock (PLAN-auth-and-case-locking.md Phase 1): read-only banner + disabled
  // inputs when another tab/user holds it; heartbeat + release-on-close when we do.
  onCaseLoaded('pt', S.ptCase.key, d.lock, d.read_only);
  if (!d.read_only) goToPanel('panel-pt-seq');
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
    { method: 'POST', btn, busyLabel: 'Extracting…', llm: true }, ptStatusEl('pt-seq-status'));
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
  // Chosen-record snapshots first (save_matches `records`, 2026-08-26): they keep
  // keyword-search picks rendering with real db/cov/why after a reload instead of
  // degrading to 'other'/'?'. Cache-only — they don't create candidate rows.
  Object.values(st3.records || {}).forEach(r => _ptCacheRecs([r]));
  (st3.matches || []).forEach(m => {
    _ptCacheRecs([m]);
    (m.covers_steps || []).forEach(n => {
      if (!_ptStepCands[n]) _ptStepCands[n] = [];
      if (!_ptStepCands[n].some(x => x.id === m.id)) _ptStepCands[n].push(m);
    });
  });
  // Persisted per-step suggestions (step3.step_matches, 2026-08-26) — these are
  // what make suggest results survive a reload / a closed browser. Seeded LAST
  // and REPLACING on id-collision: a step-scoped verdict outranks the whole-case
  // one for that step, in both the candidate pool and the record cache.
  const sm = st3.step_matches || {};
  Object.keys(sm).forEach(nk => {
    const n = Number(nk);
    (sm[nk] || []).forEach(m => {
      if (!m || !m.id) return;
      _ptCacheRecs([m]);
      const pool = _ptStepCands[n] = _ptStepCands[n] || [];
      const i = pool.findIndex(x => x.id === m.id);
      if (i >= 0) pool[i] = { ...pool[i], ...m }; else pool.push(m);
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

// The per-step suggest URL for the step currently on screen — same call ptSuggestStep
// makes, so the previewed prompt is 1-for-1 with a real send (provenance.js's contract).
function ptStepSuggestEndpoint() {
  const seq = _ptSeq();
  const n = (seq[_ptCurStep] || seq[0] || {}).n || 1;
  return `${PT_API}/suggest_scripts_step/${encodeURIComponent(S.ptCase.key)}/${n}`;
}

export function renderPtSearchPanel() {
  const el = document.getElementById('pt-steps-list');
  if (!ptSession) { if (el) el.innerHTML = '<em class="review-empty">Load a case first.</em>'; return; }
  const st3 = ptSession.step3 || {};
  _ptSeedFromSession();
  _ptCurStep = 0;                    // entering the panel starts at the first step
  ptRenderSteps();
  _ptBindStepSearch();
  // Points at the endpoint the panel ACTUALLY drives. It was wired to the whole-case
  // /suggest_scripts, which left the UI on 2026-08-20 when the per-step picker replaced
  // it (this was its last reference in the frontend) — so Refresh rendered the retired
  // mega-prompt: a prompt this flow never sends, presented as "what would be sent".
  // Resolved at click time, so it follows whichever step the pager is on.
  mountPtProvenance('pt-match-prov', 'panel-pt-search', ptStepSuggestEndpoint,
                    st3.provenance, () => ({ user_inputs: '' }));
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

  // Nav / coverage bar: suggest-all + overall tally + Prev/Next + per-step pills.
  if (sumEl) {
    const sa = _ptSuggestAll;
    const saLabel = sa
      ? (sa.stopReq ? 'Stopping after this step…'
                    : `Suggesting step ${Math.min(sa.done + 1, sa.total)}/${sa.total}… (click to stop)`)
      : 'Suggest all steps (LLM)';
    const pills = seq.map((s, i) => {
      const ok = (_ptStepChosen[s.n] || []).length > 0;
      const cur = i === _ptCurStep ? ' pt-pill-current' : '';
      return `<button class="pt-pill ${ok ? 'pt-pill-ok' : 'pt-pill-gap'}${cur}" `
        + `data-action="ptGoStep" data-args='[${i}]' title="Sequence step ${s.n}${ok ? ' — covered' : ' — no script yet'}">`
        + `${ok ? '✓' : '✗'} ${s.n}</button>`;
    }).join('');
    sumEl.innerHTML = `<div class="pt-stepnav">
      <button class="btn btn-primary btn-compact" data-action="ptSuggestAllSteps" id="pt-suggest-all-btn"${sa && sa.stopReq ? ' disabled' : ''}>${saLabel}</button>
      <span class="badge ${gaps ? 'badge-low' : 'badge-success'}">${covered}/${seq.length} sequence steps covered${gaps ? ` — ${gaps} gap${gaps > 1 ? 's' : ''}` : ' ✓'}</span>
      <div class="pt-stepnav-btns">
        <button class="btn btn-compact" data-action="ptPrevStep" ${_ptCurStep === 0 ? 'disabled' : ''}>‹ Prev</button>
        <span class="pt-stepnav-pos">Sequence step ${_ptCurStep + 1} of ${seq.length}</span>
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
        <b>Sequence step ${n}</b> — ${escapeHtml(s.action || '')}
        <span class="justification-note">${ok ? `${chosenIds.size} chosen` : 'no script yet'}</span>
      </div>
      <div class="justification-note pt-step-verify">verify: ${escapeHtml(s.verify || '')}</div>

      <div class="compact-flex mt-1 mb-2">
        <button class="btn btn-primary btn-compact" data-action="ptSuggestStep" data-args='[${n}]' id="pt-suggest-step-${n}">Suggest for sequence step ${n} (LLM)</button>
        <input type="text" class="form-input form-input-search pt-step-q" data-step="${n}" placeholder="keyword search this step…">
        <button class="btn btn-compact" data-action="ptSearchStep" data-args='[${n}]'>Search</button>
        <span class="justification-note" id="pt-step-status-${n}"></span>
      </div>

      <div class="pt-step-sub">Candidates <span class="justification-note">— tick rows and Choose to shortlist them for this step</span></div>
      ${_ptMatchTable(cands, n, 'cand')}
      <div class="compact-flex mt-1 mb-2">
        <button class="btn btn-compact" data-action="ptChooseMatches" data-args='[${n}]'>↓ Choose ticked for sequence step ${n}</button>
      </div>

      <div class="pt-step-sub">Chosen for this sequence step <span class="justification-note">— reused for sequence step ${n}; tick and Remove to move back up</span></div>
      ${_ptMatchTable(chosenRecs, n, 'chosen')}
      <div class="compact-flex mt-1">
        <button class="btn btn-compact" data-action="ptClearChosen" data-args='[${n}]'>↑ Remove ticked from sequence step</button>
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

// Suggest for EVERY sequence step, one step at a time (2026-08-26, Terrence).
// Deliberately sequential — one LLM call per step in sequence order, the same
// call the per-step button makes — NOT the retired whole-case single prompt.
// Results populate each step's candidate pool as they arrive (the backend
// persists them per step, so a mid-run reload keeps every completed step) and
// stay on the page when the run finishes. Clicking again while running stops
// after the in-flight step completes.
let _ptSuggestAll = null;   // { stopReq, done, total, added, failures[] } while running

async function ptSuggestAllSteps() {
  if (!ptRequireCase()) return;
  if (_ptSuggestAll) {
    _ptSuggestAll.stopReq = true;
    cancelLlmCall(_ptSuggestAll.callId);   // true cancel of the in-flight step too
    ptRenderSteps();
    return;
  }
  const seq = _ptSeq();
  if (!seq.length) { alert('No sequence — confirm step 2 first.'); return; }
  _ptSuggestAll = { stopReq: false, done: 0, total: seq.length, added: 0, failures: [] };
  ptRenderSteps();
  const st = ptStatusEl('pt-search-status');
  for (const s of seq) {
    if (_ptSuggestAll.stopReq) break;
    const n = s.n;
    if (st) st.textContent = `Suggesting for sequence step ${n} (${_ptSuggestAll.done + 1}/${_ptSuggestAll.total})…`;
    _ptSuggestAll.callId = newCallId();
    const d = await ptApi(`/suggest_scripts_step/${S.ptCase.key}/${n}`, {
      method: 'POST',
      body: JSON.stringify({ user_inputs: '' }),
      headers: { 'X-CK-LLM-Call': _ptSuggestAll.callId },
    }, st);
    recordLLMDebug(document.getElementById('pt-suggest-all-btn'));
    if (d) {
      _ptAddCands(n, d.matches || []);
      _ptSuggestAll.added += (d.matches || []).length;
    } else if (!_ptSuggestAll.stopReq) {
      // null with stopReq set is the user's own cancel, not a failure
      _ptSuggestAll.failures.push(n);
    }
    _ptSuggestAll.done += 1;
    ptRenderSteps();
  }
  const run = _ptSuggestAll;
  _ptSuggestAll = null;
  ptRenderSteps();
  if (st) {
    const failed = run.failures.length ? ` — FAILED on step(s) ${run.failures.join(', ')}` : '';
    st.textContent = (run.stopReq && run.done < run.total ? `⏹ Stopped after ${run.done}/${run.total} steps` : `Suggested all ${run.total} steps`)
      + ` — ${run.added} match(es) added${failed}. Results are saved with the case.`;
  }
}

// Per-step LLM suggest — links every result to this step.
async function ptSuggestStep(stepN) {
  if (!ptRequireCase()) return;
  const btn = document.getElementById(`pt-suggest-step-${stepN}`);
  const st = document.getElementById(`pt-step-status-${stepN}`);
  const d = await ptApi(`/suggest_scripts_step/${S.ptCase.key}/${stepN}`, {
    method: 'POST',
    body: JSON.stringify({ user_inputs: '' }),
    btn, busyLabel: 'Suggesting…', llm: true,
  }, st);
  recordLLMDebug(btn);
  if (!d) return;
  _ptAddCands(stepN, d.matches || []);
  ptRenderSteps();
  const el = document.getElementById(`pt-step-status-${stepN}`);
  if (el) el.textContent = `${(d.matches || []).length} match(es) for sequence step ${stepN}.`;
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
  if (el) el.textContent = `${recs.length} hit(s) for "${q}" — linked to sequence step ${stepN}.`;
}

async function ptSaveMatches() {
  if (!ptRequireCase()) return;
  const sel = {};
  Object.keys(_ptStepChosen).forEach(n => { if ((_ptStepChosen[n] || []).length) sel[n] = _ptStepChosen[n].slice(); });
  const total = new Set(Object.values(sel).flat()).size;
  // Send the cached record per chosen id so the server can persist db/cov/why —
  // keyword-search picks have no other persisted source (see save_matches).
  const records = {};
  Object.values(sel).flat().forEach(id => { if (_ptRecCache[id]) records[id] = _ptRecCache[id]; });
  // Pass the button: a save is a request like any other, so it gets the same
  // spinner + ✓/✗ flash every LLM button has. Without it the only sign a save
  // happened was a line of status text, and a reviewer watching the button they
  // just pressed saw nothing at all (2026-09-02).
  const btn = document.getElementById('pt-save-matches-btn');
  const d = await ptApi(`/save_matches/${S.ptCase.key}`, {
    method: 'POST', btn, busyLabel: 'Saving…', doneLabel: '✓ Saved',
    body: JSON.stringify({ selections: sel, records }),
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

// EVERY fragment key SHOWN under a step: the accounting's chosen entries plus their
// redundant nests, and any maps_to fragment the accounting did not place.
//
// THE DEFECT THIS FIXES (2026-09-02, AWPTCM-T44297)
// ------------------------------------------------
// The step body renders from `_ptFragAcct` (per-step accounting) but the coverage pill and
// the "no fragment selected" note read `_fragsForStep` (maps_to). Two sources of truth for
// one question, so they can disagree — and did: after the sequence was re-extracted from 13
// steps to 31, the fragment pool kept `maps_to` on the OLD numbering, so step 14 displayed
// three ticked fragment cards while its header said "no fragment selected" and its pill
// showed ✗. The backend merge is fixed too, but the UI must not be able to contradict what
// it is displaying even when the data is imperfect.
//
// Redundant keys count: a redundant fragment is unticked by DEFAULT, but the reviewer can
// tick it to override, and a ticked fragment serving this step does cover it.
function _fragKeysForStep(n) {
  const keys = new Set();
  (_ptFragAcct[String(n)] || []).forEach(en => {
    if (en.chosen) keys.add(_keyOf(en.chosen));
    (en.redundant || []).forEach(r => { if (r.key) keys.add(_keyOf(r.key)); });
  });
  _fragsForStep(n).forEach(f => keys.add(_fragKey(f)));
  return keys;
}

// Selected fragment keys shown under a step — what "covered" actually means here.
function _selectedKeysForStep(n) {
  return Array.from(_fragKeysForStep(n)).filter(k => _ptFragSel.has(k));
}

// How many ticked CARDS the panel paints, which is not how many fragments are
// selected. A fragment serving 26 sequence steps is ONE entry in the pool and 26
// cards on screen, so scrolling the panel and counting ticks gives a number four
// or five times the count Generate receives — on AWPTCM-T44297, 157 against 34.
// Both are honest; a save that reports only one of them invites the reader to
// check it against the other and conclude the tool is lying (2026-09-02).
function _selectedCardCount() {
  return _ptSeq().reduce((n, s) => n + _selectedKeysForStep(s.n).length, 0);
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

  // A step is "covered" if at least one SELECTED fragment is SHOWN under it — the same
  // set the body renders, so the pill can never contradict the cards (see _fragKeysForStep).
  const stepHasSel = (n) => _selectedKeysForStep(n).length > 0;
  const covered = seq.filter(s => stepHasSel(s.n)).length;
  const gaps = seq.length - covered;
  if (sumEl) {
    const pills = seq.map((s, i) => {
      const ok = stepHasSel(s.n);
      const cur = i === _ptFragStep ? ' pt-pill-current' : '';
      return `<button class="pt-pill ${ok ? 'pt-pill-ok' : 'pt-pill-gap'}${cur}" data-action="ptFragGoStep" data-args='[${i}]' title="Sequence step ${s.n}${ok ? ' — has a selected fragment' : ' — none selected'}">${ok ? '✓' : '✗'} ${s.n}</button>`;
    }).join('');
    sumEl.innerHTML = staleBanner + `<div class="pt-stepnav">
      <span class="badge ${gaps ? 'badge-low' : 'badge-success'}">${covered}/${seq.length} steps with a selected fragment${gaps ? ` — ${gaps} gap${gaps > 1 ? 's' : ''}` : ' ✓'}</span>
      <div class="pt-stepnav-btns">
        <button class="btn btn-compact" data-action="ptFragPrevStep" ${_ptFragStep === 0 ? 'disabled' : ''}>‹ Prev</button>
        <span class="pt-stepnav-pos">Sequence step ${_ptFragStep + 1} of ${seq.length}</span>
        <button class="btn btn-compact" data-action="ptFragNextStep" ${_ptFragStep === seq.length - 1 ? 'disabled' : ''}>Next ›</button>
      </div>
      <div class="pt-pill-row">${pills}</div>
    </div>`;
  }

  const s = seq[_ptFragStep];
  const n = s.n;
  const selCount = _selectedKeysForStep(n).length;
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
        <b>Sequence step ${n}</b> — ${escapeHtml(s.action || '')}
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
    { method: 'POST', btn, busyLabel: 'Gathering…', llm: true }, ptStatusEl('pt-frag-status'));
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
  // btn + a status span BESIDE the button, not #pt-frag-status up beside Gather:
  // on a 31-step case that one is a screen-height away, so the save read as a no-op.
  const btn = document.getElementById('pt-save-frag-btn');
  const st = ptStatusEl('pt-frag-save-status');
  const d = await ptApi(`/save_fragments/${S.ptCase.key}`, {
    method: 'POST', btn, busyLabel: 'Saving…', doneLabel: '✓ Saved',
    body: JSON.stringify({ keep }),
  }, st);
  if (!d) return;
  await ptRefreshSession();
  if (!st) return;
  const cards = _selectedCardCount();
  // The card count is only worth saying when it differs — on a case where every
  // fragment serves one step the two numbers are equal and the parenthetical is noise.
  st.textContent = cards > keep.length
    ? `Saved — ${keep.length} unique fragment(s) `
      + `(${cards} ticked card(s) across ${_ptSeq().length} step(s)) selected for generation.`
    : `Saved — ${keep.length} fragment(s) selected for generation.`;
}

// --- Step 6 (shown as "5. Generate"): PER-UNIT generation ---------------------
//
// PLAN-pytest-creator.md §9.5. One LLM call per unit — a single TestCase class, or the
// TestSet configure()/tear_down() pair — spliced into a frame the SERVER renders. The
// frame is not a model's work, so it cannot drift between units.
//
// Pills mirror Script Search's page-within-a-page: red = not generated, yellow = in
// flight, green = returned, plus a final Summary pill that is red until every unit is
// green. Each unit page shows what came back on top and the prompt that will be sent
// below, editable — the per-unit button sends what is on screen, verbatim.
let _ptUnits = [];          // [{id, kind, label, prompt, code, status, ...}] from /step_prompts
let _ptUnitIdx = 0;         // viewer position; _PT_SUMMARY selects the Summary page
let _ptUnitSending = {};    // id -> true while a call is in flight (the yellow state)
let _ptUnitFails = [];      // [{id, label, why, at}] surfaced as they land
const _PT_SUMMARY = -1;

// Prompts live in JS, not in 30 textareas. Only one unit page is in the DOM at a time,
// but "fire them all" has to send every unit's CURRENT text — including edits made on a
// page since navigated away from. So an edit writes back into _ptUnits immediately.
function _ptUnitById(id) { return _ptUnits.find(u => u.id === id) || null; }

function _ptUnitState(u) {
  if (_ptUnitSending[u.id]) return 'run';
  // STATUS, not "do we happen to have the code cached". The status poll deliberately does
  // not ship code back (30 units x ~2.5KB every 2s is 150KB/minute of unchanged bytes), so
  // a unit that lands while others are still running has status 'ok' and no local code. It
  // was requiring both, which left every early finisher red until the whole run ended.
  if (u.status === 'ok') return 'ok';
  return 'gap';                            // pending OR error — both are "not generated"
}

function ptRenderUnitPills() {
  const el = document.getElementById('pt-unit-pills');
  if (!el) return;
  if (!_ptUnits.length) { el.innerHTML = ''; return; }
  const cls = { ok: 'pt-pill-ok', run: 'pt-pill-run', gap: 'pt-pill-gap' };
  const pills = _ptUnits.map((u, i) => {
    const st = _ptUnitState(u);
    const glyph = st === 'ok' ? '✓' : (st === 'run' ? '…' : '✗');
    const cur = (i === _ptUnitIdx) ? ' pt-pill-current' : '';
    const label = u.kind === 'setup' ? 'setup' : String(u.tc_n);
    const why = u.status === 'error' && u.error ? ` — FAILED: ${u.error}` : '';
    return `<button class="pt-pill ${cls[st]}${cur}" data-action="ptGoUnit" data-args='[${i}]' `
      + `title="${escapeHtml(u.label)}${escapeHtml(why)}">${glyph} ${escapeHtml(label)}</button>`;
  }).join('');
  // Summary is red until every unit is green, then YELLOW — not green. Green is earned by
  // assembling and passing the checks, not by the units merely existing.
  const done = _ptUnits.every(u => _ptUnitState(u) === 'ok');
  const assembled = !!((ptSession && (ptSession.step6 || {}).assembled_at));
  const lintOk = !!(((ptSession || {}).step6 || {}).lint || {}).ok;
  const sumCls = (done && assembled && lintOk) ? 'pt-pill-ok' : (done ? 'pt-pill-run' : 'pt-pill-gap');
  const sumGlyph = (done && assembled && lintOk) ? '✓' : (done ? '…' : '✗');
  const sumCur = (_ptUnitIdx === _PT_SUMMARY) ? ' pt-pill-current' : '';
  el.innerHTML = pills
    + `<button class="pt-pill ${sumCls}${sumCur}" data-action="ptGoSummary" `
    + `title="Assemble the units into the frame, lint, review">${sumGlyph} Summary</button>`;
  const st = document.getElementById('pt-units-status');
  if (st && !st.dataset.busy) {
    const n = _ptUnits.filter(u => _ptUnitState(u) === 'ok').length;
    st.textContent = `${n}/${_ptUnits.length} unit(s) generated.`;
  }
}

// Failures surface as a NON-BLOCKING panel, not window.alert(). A blocking alert freezes
// the JS event loop, so during a concurrent fan-out every other unit's result would queue
// behind the dialog — and 29 sequential alerts cannot be dismissed faster than they
// arrive. This appears the instant a failure lands (the ask) and names the unit, with a
// re-run on the row.
function ptRenderUnitErrors() {
  const el = document.getElementById('pt-unit-errors');
  if (!el) return;
  if (!_ptUnitFails.length) { el.innerHTML = ''; return; }
  el.innerHTML = '<div class="pt-unit-errbox"><b>✗ ' + _ptUnitFails.length
    + ' unit(s) failed</b> <button class="btn btn-compact-small" data-action="ptClearUnitErrors">dismiss</button>'
    + _ptUnitFails.map(f => `<div class="pt-unit-errrow">
        <b>${escapeHtml(f.label)}</b> — ${escapeHtml(f.why)}
        <button class="btn btn-compact-small" data-action="ptGenerateUnit" data-args='["${escapeHtml(f.id)}"]'>re-run</button>
      </div>`).join('') + '</div>';
}

function ptClearUnitErrors() { _ptUnitFails = []; ptRenderUnitErrors(); }

function ptRenderUnitPage() {
  const el = document.getElementById('pt-unit-page');
  const sum = document.getElementById('pt-summary-page');
  if (!el || !sum) return;
  if (_ptUnitIdx === _PT_SUMMARY) {
    el.innerHTML = '';
    sum.classList.remove('hidden');
    return;
  }
  sum.classList.add('hidden');
  const u = _ptUnits[_ptUnitIdx];
  if (!u) { el.innerHTML = '<em class="review-empty">No units — confirm step 4 first.</em>'; return; }
  const st = _ptUnitState(u);
  const head = u.kind === 'setup'
    ? '<b>TestSet.configure() / tear_down()</b> <span class="justification-note">the suite setup pair — config only, no pass/fail</span>'
    : `<b>${escapeHtml(u.label)}</b> <span class="justification-note">implements sequence step ${escapeHtml(String(u.source_n))}</span>`;
  const contract = u.kind === 'setup' ? '' : `
    <div class="justification-note mt-1"><b>action:</b> ${escapeHtml(u.action || '')}</div>
    <div class="justification-note"><b>verify:</b> ${escapeHtml(u.verify || '')}</div>`;
  el.innerHTML = `
    <div class="compact-flex">
      <button class="btn btn-compact" data-action="ptUnitPrev" ${_ptUnitIdx === 0 ? 'disabled' : ''}>‹ Prev</button>
      <span class="justification-note">unit ${_ptUnitIdx + 1} / ${_ptUnits.length}</span>
      <button class="btn btn-compact" data-action="ptUnitNext" ${_ptUnitIdx >= _ptUnits.length - 1 ? 'disabled' : ''}>Next ›</button>
    </div>
    <div class="mt-2">${head}${contract}</div>
    <div class="compact-flex mt-2">
      <button class="btn btn-primary btn-compact" data-action="ptGenerateUnit" data-args='["${escapeHtml(u.id)}"]' id="pt-unit-btn">Generate ${escapeHtml(u.kind === 'setup' ? 'setup' : u.label)} (LLM)</button>
      <span class="justification-note" id="pt-unit-status">${
        st === 'ok' ? '✓ returned ' + escapeHtml(u.at || '')
        : (u.status === 'error' ? '✗ ' + escapeHtml(u.error || 'failed')
        : (st === 'run' ? 'in flight…' : 'not generated yet'))}</span>
      ${u.edited ? '<span class="badge">prompt edited</span>' : ''}
    </div>

    <div class="pt-unit-frame mt-2">
      <div class="pt-unit-frame-label">Returned code — what the LLM sent back for this unit</div>
      <pre id="pt-unit-out" class="session-pre pt-unit-out">${
        u.code ? escapeHtml(u.code)
        : (u.status === 'ok'
           ? '(returned — loading…)'
           : (u.status === 'error'
              ? '(refused — see the reply below)'
              : '(nothing yet — press Generate)'))}</pre>
    </div>
    ${u.status === 'error' && u.raw ? `
    <div class="pt-unit-frame pt-unit-frame-raw mt-2">
      <div class="pt-unit-frame-label">Refused reply — kept so you can see WHY it was rejected</div>
      <pre class="session-pre pt-unit-out">${escapeHtml(u.raw)}</pre>
    </div>` : ''}

    <div class="pt-unit-frame mt-2">
      <div class="pt-unit-frame-label">Prompt being sent — editable; the button above sends exactly this</div>
      <textarea id="pt-unit-prompt" class="form-input editor-textarea pt-unit-prompt" spellcheck="false">${escapeHtml(u.prompt || '')}</textarea>
      <div class="justification-note">${(u.prompt || '').length} chars. Edits are kept for this session and persist with the case once the unit is generated.</div>
    </div>`;
  // Fetch on OPEN — the behaviour units_status's docstring has always claimed. Covers both
  // "landed while others are still running" and "regenerated, cached copy just dropped".
  if ((u.status === 'ok' && !u.code) || (u.status === 'error' && !u.raw)) _ptFetchUnitCode(u.id);

  const ta = document.getElementById('pt-unit-prompt');
  if (ta) ta.addEventListener('input', () => {
    // Write back immediately: only one page is in the DOM, and "fire them all" must send
    // the edit you made on a page you have since navigated away from.
    const cur = _ptUnits[_ptUnitIdx];
    if (cur) { cur.prompt = ta.value; cur._dirty = true; }
  });
}

// Units whose code we are already fetching, so re-rendering cannot start a second
// request for the same unit (ptRenderUnitPage runs on every poll tick).
const _ptUnitCodeFetching = {};

// Pull ONE unit's stored reply. The status poll deliberately ships no code, so this is how
// a landed unit becomes readable without waiting for the whole fan-out to finish.
async function _ptFetchUnitCode(id) {
  if (!S.ptCase || _ptUnitCodeFetching[id]) return;
  _ptUnitCodeFetching[id] = true;
  try {
    const r = await fetch(`${PT_API}/unit_code/${encodeURIComponent(S.ptCase.key)}/${encodeURIComponent(id)}`);
    if (!r.ok) return;
    const d = await r.json();
    const u = _ptUnitById(id);
    if (!u) return;
    // Only accept the reply if the unit has not moved on while we were waiting.
    if (d.at && u.at && d.at !== u.at) return;
    u.code = d.code || '';
    u.raw = d.raw || '';
    if (d.at) u.at = d.at;
    if (_ptUnits[_ptUnitIdx] && _ptUnits[_ptUnitIdx].id === id) ptRenderUnitPage();
  } catch (_) {
    /* a dropped fetch just leaves the placeholder; the next render retries */
  } finally {
    delete _ptUnitCodeFetching[id];
  }
}

function ptRenderUnits() { ptRenderUnitPills(); ptRenderUnitErrors(); ptRenderUnitPage(); }

function ptGoUnit(i) { _ptUnitIdx = i; ptRenderUnits(); }
function ptGoSummary() { _ptUnitIdx = _PT_SUMMARY; ptRenderUnits(); renderPtGenPanel(); }
function ptUnitPrev() { if (_ptUnitIdx > 0) { _ptUnitIdx -= 1; ptRenderUnits(); } }
function ptUnitNext() { if (_ptUnitIdx < _ptUnits.length - 1) { _ptUnitIdx += 1; ptRenderUnits(); } }

async function ptLoadUnits() {
  if (!ptRequireCase()) return;
  const btn = document.getElementById('pt-units-reload-btn');
  const d = await ptApi(`/step_prompts/${S.ptCase.key}`, { btn, busyLabel: 'Rendering…' },
                        ptStatusEl('pt-units-status'));
  if (!d) return;
  // Preserve any UNSENT edit across a re-render: the server re-renders from the template,
  // and silently replacing text the reviewer typed would be the same defect as
  // re-rendering at dispatch.
  const edits = {};
  _ptUnits.forEach(u => { if (u._dirty) edits[u.id] = u.prompt; });
  _ptUnits = (d.units || []).map(u => ({ ...u, prompt: edits[u.id] || u.prompt,
                                         _dirty: !!edits[u.id] }));
  if (_ptUnitIdx >= _ptUnits.length) _ptUnitIdx = 0;
  ptRenderUnits();
}

// ONE request dispatches, ONE request polls. Never a connection per unit.
//
// THE DEADLOCK THIS REPLACES (2026-09-02, found on the live server)
// -----------------------------------------------------------------
// This used to POST /generate_step per unit and await each. Every such request holds its
// connection for the whole LLM call — it blocks server-side in registry.submit until the
// browser posts a result. A browser allows SIX connections per origin. So 30 requests
// fired, 6 took every connection and blocked, and the broker's own /api/agent/next
// long-poll could not get one. Nothing was claimed, nothing returned, no connection was
// freed. Live evidence: pending:5 (only ~6 of 30 requests reached the server at all),
// session_active:false, zero claude processes, zero LLM records. Raising ckBrokerWorkers
// made it worse — each worker holds a long-poll on the same origin.
//
// The jsdom spec could not have caught it: a stubbed fetch has no connection limit. It
// proved this code dispatches concurrently, not that the transport could carry it.
const _PT_UNIT_POLL_MS = 2000;
let _ptUnitPoll = null;

function _ptStopUnitPoll() {
  if (_ptUnitPoll) { clearInterval(_ptUnitPoll); _ptUnitPoll = null; }
}

// Merge a status snapshot onto the local units. Code is fetched per page, not per poll:
// 30 units of ~2.5KB every 2s is 150KB/minute of unchanged bytes.
function _ptApplyUnitStatus(map, running) {
  let settledSomething = false;
  const runSet = new Set(running || []);
  _ptUnits.forEach(u => {
    const st = map[u.id];
    const wasSending = !!_ptUnitSending[u.id];
    if (runSet.has(u.id)) { _ptUnitSending[u.id] = true; return; }
    if (wasSending) { delete _ptUnitSending[u.id]; settledSomething = true; }
    if (!st) return;
    if (st.status === 'ok') {
      // `at` is the discriminator, NOT `status`. A unit generated by an EARLIER run is
      // already 'ok' at page load, so keying on the status transition never fired for it
      // and the page kept showing that run's code under that run's timestamp while this
      // run quietly replaced it on the server — stale output presented as current, which
      // is worse than showing nothing. Terrence caught it on TestCase_2 and TestCase_9,
      // 2026-09-02. Any change of `at` means new bytes exist: drop what we cached.
      if (st.at && st.at !== u.at) { u.at = st.at; u.code = ''; u.raw = ''; }
      if (u.status !== 'ok') { u.status = 'ok'; u.error = ''; u.at = st.at || u.at; }
    } else if (st.status === 'error') {
      if (u.status !== 'error' || u.error !== st.error || (st.at && st.at !== u.at)) {
        u.status = 'error';
        u.error = st.error || 'failed';
        u.at = st.at || u.at;
        u.code = ''; u.raw = '';          // a failed re-run must not keep the old success
        // Surfaced the moment we learn of it, which is the ask — but in a panel, because
        // window.alert would freeze the event loop mid-fan-out.
        if (!_ptUnitFails.some(f => f.id === u.id)) {
          _ptUnitFails.push({ id: u.id, label: u.label, why: u.error,
                              at: new Date().toISOString() });
        }
      }
    }
  });
  return settledSomething;
}

async function _ptPollUnitsOnce() {
  let d = null;
  try {
    const r = await fetch(`${PT_API}/units_status/${encodeURIComponent(S.ptCase.key)}`);
    if (!r.ok) return false;
    d = await r.json();
  } catch (_) { return false; }          // a dropped poll is not a failure of the work
  _ptApplyUnitStatus(d.units || {}, d.running || []);
  ptRenderUnits();
  const stillRunning = (d.running || []).length > 0;
  if (!stillRunning) {
    _ptStopUnitPoll();
    // Pull the code for whatever landed, once, now that nothing is in flight.
    await ptLoadUnits();
    const st = ptStatusEl('pt-units-status');
    if (st) {
      delete st.dataset.busy;
      const ok = _ptUnits.filter(u => _ptUnitState(u) === 'ok').length;
      st.textContent = `${ok}/${_ptUnits.length} unit(s) generated`
        + (_ptUnitFails.length ? ` — ${_ptUnitFails.length} failed; re-run them individually.` : '.');
    }
  }
  return stillRunning;
}

function _ptStartUnitPoll() {
  _ptStopUnitPoll();
  _ptUnitPoll = setInterval(_ptPollUnitsOnce, _PT_UNIT_POLL_MS);
}

// Dispatch a subset (or all) and start polling. `ids` empty = every unit.
async function _ptDispatchUnits(ids) {
  const wanted = (ids && ids.length ? ids : _ptUnits.map(u => u.id));
  const payload = wanted.map(id => {
    const u = _ptUnitById(id);
    return { id, prompt: (u && u.prompt) || '' };
  });
  wanted.forEach(id => { _ptUnitSending[id] = true; });
  _ptUnitFails = _ptUnitFails.filter(f => !wanted.includes(f.id));
  ptRenderUnits();
  const errRef = {};
  const d = await ptApi(`/generate_units/${S.ptCase.key}`, {
    method: 'POST', body: JSON.stringify({ units: payload }), errRef,
  }, null);
  if (!d) {
    wanted.forEach(id => { delete _ptUnitSending[id]; });
    _ptUnitFails.push({ id: wanted[0] || '?', label: 'dispatch',
                        why: errRef.msg || 'could not dispatch', at: new Date().toISOString() });
    ptRenderUnits();
    return null;
  }
  // Anything the server refused to (re)dispatch is not in flight.
  const live = new Set([...(d.dispatched || []), ...(d.already_running || [])]);
  wanted.forEach(id => { if (!live.has(id)) delete _ptUnitSending[id]; });
  ptRenderUnits();
  _ptStartUnitPoll();
  return d;
}

async function ptGenerateUnit(unitId) {
  if (!ptRequireCase()) return;
  if (!_ptUnitById(unitId)) return;
  if (_ptUnitSending[unitId]) return;                 // already in flight
  return await _ptDispatchUnits([unitId]);
}

async function ptGenerateAllUnits() {
  if (!ptRequireCase()) return;
  if (!_ptUnits.length) await ptLoadUnits();
  const btn = document.getElementById('pt-units-all-btn');
  const st = ptStatusEl('pt-units-status');
  if (st) { st.dataset.busy = '1'; st.textContent = `Dispatching ${_ptUnits.length} unit(s)…`; }
  // The button's job ends when dispatch returns; the pills carry progress from there.
  setButtonBusy(btn, true, { label: 'Dispatching…' });
  const d = await _ptDispatchUnits(null);
  setButtonBusy(btn, false);
  flashButtonDone(btn, !!d, d ? { label: `✓ ${(d.dispatched || []).length} sent` } : undefined);
  if (st && d) {
    st.textContent = `${(d.dispatched || []).length} unit(s) dispatched — `
      + `up to ${d.max_concurrent} at once server-side, and however many the broker's `
      + `workers can run. Pills update as they land.`;
  }
}

async function ptAssembleScript() {
  if (!ptRequireCase()) return;
  const btn = document.getElementById('pt-assemble-btn');
  // LOCAL: splice + re-stamp + manifest + lint. No LLM, so no llm:true and no Stop.
  const d = await ptApi(`/assemble_script/${S.ptCase.key}`, {
    method: 'POST', btn, busyLabel: 'Assembling…',
    body: JSON.stringify(ptGenNaming()),
  }, ptStatusEl('pt-gen-status'));
  if (!d) return;
  await ptRefreshSession();
  renderPtGenPanel();
  ptRenderUnits();
  ptStatusEl('pt-gen-status').textContent =
    `Assembled ${d.units} unit(s) — manifest ${d.manifest && d.manifest.ok ? 'ok' : 'FAILED'}, `
    + `lint ${d.lint && d.lint.ok ? 'ok' : 'FAILED'}. Run Review for the holistic pass.`;
}

// --- Step 6: Generate ---------------------------------------------------------

function ptUpdateGenPath() {
  const g = document.getElementById('pt-gen-group').value.trim() || '<Group>';
  const n = document.getElementById('pt-gen-name').value.trim() || '<Name>';
  document.getElementById('pt-gen-path').textContent = `→ generated/${g}/${n}.py`;
}

// The step-6 naming as the page currently shows it — one reader for the dry-run body,
// the autosave and (by shape) what ptGenerateScript posts.
function ptGenNaming() {
  return {
    group: (document.getElementById('pt-gen-group').value || '').trim(),
    name: (document.getElementById('pt-gen-name').value || '').trim(),
  };
}

// Best-effort persistence of the naming fields alone. Silent by design: this fires on
// blur, so a 409 (a script already exists — Save to generated/ owns the rename then) or a
// 400 (half-typed name) must not throw a dialog at someone who is simply tabbing between
// fields. The Generate and Save buttons still surface those errors properly.
async function ptSaveGenNaming() {
  if (!S.ptCase || !ptSession) return;
  const { group, name } = ptGenNaming();
  if (!group || !name) return;
  const cur = (ptSession.step6 || {}).naming || {};
  if (cur.group === group && cur.name === name) return;
  try {
    const res = await fetch(`${PT_API}/save_naming/${encodeURIComponent(S.ptCase.key)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ group, name }),
    });
    if (!res.ok) return;
    const d = await res.json();
    ptSession.step6 = { ...(ptSession.step6 || {}), naming: d.naming };
  } catch (e) { /* offline / navigating away — the field is still on screen */ }
}

export function renderPtGenPanel() {
  if (!ptSession) { ptStatusEl('pt-gen-status').textContent = 'Load a case first.'; return; }
  // Seed the unit prompts on first entry. Not awaited: the rest of the panel renders
  // immediately and the pills fill in when the render returns.
  if (!_ptUnits.length) { ptLoadUnits(); } else { ptRenderUnits(); }
  const s6 = ptSession.step6 || {};
  const naming = s6.naming || {};
  const groupEl = document.getElementById('pt-gen-group');
  const nameEl = document.getElementById('pt-gen-name');
  groupEl.value = naming.group || (ptCaseInfo ? ptCaseInfo.group_display : '');
  nameEl.value = naming.name || '';
  groupEl.oninput = ptUpdateGenPath;
  nameEl.oninput = ptUpdateGenPath;
  // Autosave on blur. Until a generation SUCCEEDS the server has no other writer for these
  // two fields (save_script 409s without a file), so an edit lived only in the DOM and the
  // re-seed above quietly restored the default when the panel was left and re-entered.
  groupEl.onblur = ptSaveGenNaming;
  nameEl.onblur = ptSaveGenNaming;
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
  // Re-seed the review from the session, or a reload silently discards findings the
  // reviewer paid an LLM call for — and an empty panel reads as "no findings".
  ptRenderReview(s6.review);
  if (s6.iterations) ptStatusEl('pt-gen-status').textContent = `Iteration ${s6.iterations}.`;
  // Generate + Fix both write step6; the provenance block covers generate_script.
  // Fix reuses the same block via its own endpoint on Refresh from the Gen panel.
  mountPtProvenance('pt-gen-prov', 'panel-pt-gen', '/api/pytest-create/generate_script/{key}',
                    s6.provenance, ptGenNaming);
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

// Pass C — the holistic review (PLAN-pytest-creator.md §9.6).
//
// Renders FINDINGS. There is deliberately no "apply" button here: §9.6 settles that a
// review must not rewrite the script, because a rewrite re-emits the whole file (the same
// wall clock chunking exists to avoid) and can silently undo a correct reused fragment,
// breaking the provenance chain. A finding becomes a change through the step-7 Fix loop,
// where it is recorded and reviewable.
const _PT_SEV = { high: '✗', medium: '△', low: '·' };

function ptRenderReview(review) {
  const el = document.getElementById('pt-review-result');
  if (!el) return;
  if (!review || !review.at) { el.innerHTML = ''; return; }
  const findings = review.findings || [];
  if (!findings.length) {
    // "No findings" is a real result, not an empty state — say so, or a reviewer cannot
    // tell a clean review from a review that never ran.
    el.innerHTML = '<span class="badge badge-success">review: no findings</span>'
      + `<div class="justification-note">Reviewed ${escapeHtml(review.at)} — nothing found beyond the static checks.</div>`;
    return;
  }
  const counts = ['high', 'medium', 'low']
    .map(sv => ({ sv, n: findings.filter(f => f.severity === sv).length }))
    .filter(c => c.n).map(c => `${c.n} ${c.sv}`).join(' · ');
  el.innerHTML = `<span class="badge">review: ${findings.length} finding(s)</span> `
    + `<span class="justification-note">${escapeHtml(counts)} — feed to the Fix button (here, or on step 7 Validate).</span>`
    + '<div class="mt-1">' + findings.map(f => `
      <div class="pt-review-finding pt-review-${escapeHtml(f.severity)}">
        <div><b>${_PT_SEV[f.severity] || '·'} ${escapeHtml(f.where || '(script)')}</b>`
        + (f.step ? ` <span class="justification-note">step ${escapeHtml(f.step)}</span>` : '')
        + ` <span class="justification-note">${escapeHtml(f.kind)}</span></div>
        <div>${escapeHtml(f.what)}</div>`
        + (f.evidence ? `<pre class="session-pre pt-review-ev">${escapeHtml(f.evidence)}</pre>` : '')
        + (f.suggestion ? `<div class="justification-note">suggested: ${escapeHtml(f.suggestion)}</div>` : '')
        + '</div>').join('') + '</div>';
}

// Fix from the SUMMARY step (2026-09-04, "Both"). Same fix_script endpoint as the step-7
// button, but reachable here so a BLOCKING error — which bars Confirm and therefore hides
// the step-7 Fix button behind an unreachable gate — can still be repaired. fix_script
// reads its reasons off the session (lint errors + review findings + any failed run), so
// no body is needed. It rewrites the WHOLE file: a following Assemble re-splices the units
// and would discard it, so the status says so and we stay on this panel.
async function ptFixFromSummary() {
  if (!ptRequireCase()) return;
  await ptPushCodeEdits(false);           // fix the script the reviewer can see, not a stale copy
  const btn = document.getElementById('pt-fix-summary-btn');
  const d = await ptApi(`/fix_script/${S.ptCase.key}`,
    { method: 'POST', btn, busyLabel: 'Fixing…', llm: true }, ptStatusEl('pt-gen-status'));
  await recordLLMDebug(btn);
  if (!d) return;
  await ptRefreshSession();
  renderPtGenPanel();
  ptStatusEl('pt-gen-status').textContent =
    `Revised whole script (iteration ${d.iterations}); previous archived. Lint is refreshed and `
    + `the old review was cleared (it described the pre-fix code) — re-run Review to see what remains. `
    + `Don't re-Assemble (it re-splices the units and discards this). Then Save & Confirm.`;
}

async function ptReviewScript() {
  if (!ptRequireCase()) return;
  // Push edits first, exactly as Lint does — reviewing the session copy while the textarea
  // holds something else reports findings against a script the reviewer cannot see.
  await ptPushCodeEdits(false);
  const btn = document.getElementById('pt-review-btn');
  const d = await ptApi(`/review_script/${S.ptCase.key}`, {
    method: 'POST', btn, busyLabel: 'Reviewing…', llm: true,
  }, ptStatusEl('pt-gen-status'));
  recordLLMDebug(btn);
  if (!d) return;
  await ptRefreshSession();
  ptRenderReview(d);
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
    btn, busyLabel: 'Generating…', llm: true,
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

// Both the Run and Validate panels used to name no case at all, which on a
// shared server meant the two most consequential panels — one runs code on
// hardware, the other closes a case out — gave no way to tell WHAT they were
// about to act on. Mirrors the line renderPtSeqPanel already draws.
function ptRenderCaseLine(elId, extra) {
  const el = document.getElementById(elId);
  if (!el) return;
  if (!S.ptCase.key || !ptSession) {
    el.innerHTML = '<em class="review-empty">No case loaded — go to </em>'
      + '<a href="#" data-action="goToPanel" data-args="[&quot;panel-pt-cases&quot;]">1. Cases</a>.';
    return;
  }
  el.innerHTML = `<b>Case:</b> <span class="sel-label">${escapeHtml(S.ptCase.key)}</span>`
    + (ptCaseInfo && ptCaseInfo.title ? ` — ${escapeHtml(ptCaseInfo.title)}` : '')
    + (extra || '');
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
  // Same shape as ptUpdateGenPath(): step6 stores naming {group,name}, no path.
  const naming = ((ptSession || {}).step6 || {}).naming || {};
  const script = (naming.group && naming.name)
    ? `generated/${naming.group}/${naming.name}.py` : null;
  ptRenderCaseLine('pt-run-case', script
    ? ` — will run <code>${escapeHtml(script)}</code>` : '');
  ptSyncRunButton();
  ptRenderRuns();
  updatePtBadges();
}

// "Run on Testbox" is the primary action and was always enabled, so the most
// consequential click in the tool was a dead one until a testbox was picked
// (ptRun only then alerted "Select a testbox."). Gate the affordance instead.
// Deliberately does NOT fight locks.js: when the lock layer has disabled the
// button it owns that state and we leave it alone.
export function ptSyncRunButton() {
  const btn = document.getElementById('pt-run-btn');
  const sel = document.getElementById('pt-run-profile');
  if (!btn || !sel) return;
  if (btn.getAttribute('data-ck-lock-disabled') === '1') return;
  const ready = !!sel.value && sel.value !== '__add__';
  btn.disabled = !ready;
  btn.title = ready ? '' : 'Select a testbox first';
}

export function ptProfileSelected(sel) {
  if (sel.value === '__add__') {
    sel.value = '';
    ptSyncRunButton();
    goToPanel('panel-pt-testbox');
    return;
  }
  ptSyncRunButton();
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
  // Stop on a terminal status, OR when the server says nothing is running for this
  // case — a run orphaned by a restart would otherwise poll forever. The server now
  // re-marks those 'stale' (_sweep_stale_runs), so this is belt-and-braces against any
  // other way `active` and `status` can disagree.
  if (['done', 'error', 'stale'].includes(d.run.status) || d.active === false) {
    clearInterval(ptRunPoll);
    ptRunPoll = null;
    if (d.active === false && !['done', 'error', 'stale'].includes(d.run.status)) {
      ptStatusEl('pt-run-status').textContent =
        `Run ${runId}: interrupted (no longer running on the server)`;
    }
  }
}

// --- Step 8: Validate ------------------------------------------------------------

export function renderPtValidatePanel() {
  ptRenderCaseLine('pt-validate-case', '');
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
    { method: 'POST', btn, busyLabel: 'Fixing…', llm: true }, ptStatusEl('pt-validate-status'));
  // Awaited (unlike the other handlers): this handler navigates to panel-pt-gen
  // below, and the record must be filed under THIS panel before currentPanel changes.
  await recordLLMDebug(btn);
  if (!d) return;
  await ptRefreshSession();
  ptStatusEl('pt-validate-status').textContent =
    `Revised (iteration ${d.iterations}); previous code archived. Review in 5. Generate, then re-run.`;
  goToPanel('panel-pt-gen');
}

// --- Testboxes (profiles CRUD) -----------------------------------------------------

export async function renderPtTestboxPanel() {
  await ptLoadProfiles();
  const el = document.getElementById('pt-tb-list');
  // The editor starts empty rather than unrendered, so its "none stored" line is
  // visible before anyone clicks edit.
  if (document.getElementById('pt-tb-setups') && !document.querySelector('#pt-tb-setups .tb-setup-row')) {
    ptRenderSetupRows([]);
  }
  const names = Object.keys(ptProfiles);
  if (!names.length) { el.innerHTML = '<em class="review-empty">No testboxes stored yet — add one below.</em>'; return; }
  let html = '<table class="table"><thead><tr><th>Name</th><th>tb</th><th>IP</th><th>User</th><th>Auth</th><th>Setups</th><th style="width:150px"></th></tr></thead><tbody>';
  names.forEach(n => {
    const p = ptProfiles[n];
    const setupNames = Object.keys(p.setups || {});
    html += `<tr><td><b>${escapeHtml(n)}</b></td><td>${escapeHtml(p.tb_number || '')}</td>
      <td class="cell-id">${escapeHtml(p.host || '')}</td><td>${escapeHtml(p.user || '')}</td>
      <td>${escapeHtml(p.auth || '')}${p.has_password ? ' (pw set)' : ''}</td>
      <td>${setupNames.length ? escapeHtml(setupNames.join(', ')) : '<span class="status-muted">—</span>'}</td>
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
  // Key names are the owner's and are reproduced verbatim, so a save round-trips
  // them unchanged instead of collapsing everything to one invented name.
  ptRenderSetupRows(Object.entries(p.setups || {}).map(([name, path]) => ({ name, path })));
  // An earlier failed save may have left fields marked; editing a row is a fresh start.
  document.querySelectorAll('#panel-pt-testbox .tb-invalid')
    .forEach(el => el.classList.remove('tb-invalid'));
  ptStatusEl('pt-tb-status').textContent = `Editing "${name}" — Save updates it.`;
}

// The four fields a testbox profile genuinely needs. `user` is here rather than
// defaulted because the server's old `st-art` fallback is wrong on some benches
// (tb470 authenticates as `terrenceb`) and produced a "Permission denied" that
// reads like a lab fault. Everything else has a working server default.
//
// `.setup` files are deliberately NOT here. A testbox profile is shared by
// everyone on this server, and each person runs their own topology, so requiring
// one at create time would just make the creator's file everyone's de-facto
// default under another name. They are a named, optional list instead.
const PT_TB_REQUIRED = [
  ['pt-tb-name', 'Name'],
  ['pt-tb-number', 'tb number'],
  ['pt-tb-host', 'Host or IP'],
  ['pt-tb-user', 'SSH user'],
];

// --- setups: a NAMED map, never a "default" ----------------------------------
// `setups` is {name: remote_path} and the Run panel renders every entry. The name
// is the owner's to choose and is preserved verbatim across an edit -- an earlier
// version of this form wrote every setup under the literal key "default", which
// silently renamed whatever was already stored and, on a shared server, meant the
// last person to save named everyone else's setup.

export function ptReadSetupRows() {
  return Array.from(document.querySelectorAll('#pt-tb-setups .tb-setup-row')).map(row => ({
    name: row.querySelector('.tb-setup-name').value.trim(),
    path: row.querySelector('.tb-setup-path').value.trim(),
  }));
}

export function ptRenderSetupRows(rows) {
  const host = document.getElementById('pt-tb-setups');
  if (!rows.length) {
    host.innerHTML = '<div class="tb-setups-empty">None stored. Runs will need a path typed into the Run panel.</div>';
    return;
  }
  host.innerHTML = rows.map((r, i) => `
    <div class="tb-setup-row">
      <input class="form-input tb-setup-name" placeholder="name (e.g. terrenceb-ie520)" value="${escapeHtml(r.name)}">
      <input class="form-input tb-setup-path" placeholder="/home/st-art/st-art/configs/tb470.setup" value="${escapeHtml(r.path)}">
      <button class="btn btn-compact" data-action="ptRemoveSetupRow" data-args="[${i}]" title="Remove this setup">&#10005;</button>
    </div>`).join('');
}

function ptAddSetupRow() {
  // Read first: re-rendering must not discard what is already typed.
  ptRenderSetupRows(ptReadSetupRows().concat([{ name: '', path: '' }]));
  const rows = document.querySelectorAll('#pt-tb-setups .tb-setup-name');
  if (rows.length) rows[rows.length - 1].focus();
}

function ptRemoveSetupRow(i) {
  const rows = ptReadSetupRows();
  rows.splice(i, 1);
  ptRenderSetupRows(rows);
}

function ptResetProfileForm() {
  ['pt-tb-name', 'pt-tb-number', 'pt-tb-host', 'pt-tb-user',
   'pt-tb-keypath', 'pt-tb-password', 'pt-tb-framework', 'pt-tb-workdir']
    .forEach(id => {
      const el = document.getElementById(id);
      if (el) { el.value = ''; el.classList.remove('tb-invalid'); }
    });
  const auth = document.getElementById('pt-tb-auth');
  if (auth) auth.value = 'key';
  ptRenderSetupRows([]);
  ptStatusEl('pt-tb-status').textContent = '';
}

async function ptSaveProfile() {
  // Validate here so a missing field reads as a named field rather than as the
  // server's generic 400, and so the offending input is visibly marked.
  const missing = [];
  PT_TB_REQUIRED.forEach(([id, label]) => {
    const el = document.getElementById(id);
    const ok = !!(el && el.value.trim());
    if (el) el.classList.toggle('tb-invalid', !ok);
    if (!ok) missing.push(label);
  });
  if (missing.length) {
    ptStatusEl('pt-tb-status').textContent = `Required: ${missing.join(', ')}.`;
    const first = document.getElementById(
      PT_TB_REQUIRED.find(([, l]) => l === missing[0])[0]);
    if (first) first.focus();
    return;
  }

  // A half-filled setup row is a mistake, not an empty one: silently dropping a
  // named row with no path would lose the entry without saying so.
  const rows = ptReadSetupRows();
  const setups = {};
  for (const r of rows) {
    if (!r.name && !r.path) continue;              // an untouched blank row
    if (!r.name || !r.path) {
      ptStatusEl('pt-tb-status').textContent =
        `Setup "${r.name || r.path}" needs both a name and a path.`;
      return;
    }
    if (Object.prototype.hasOwnProperty.call(setups, r.name)) {
      ptStatusEl('pt-tb-status').textContent = `Duplicate setup name "${r.name}".`;
      return;
    }
    setups[r.name] = r.path;
  }

  const body = {
    name: document.getElementById('pt-tb-name').value.trim(),
    tb_number: document.getElementById('pt-tb-number').value.trim(),
    host: document.getElementById('pt-tb-host').value.trim(),
    user: document.getElementById('pt-tb-user').value.trim(),
    auth: document.getElementById('pt-tb-auth').value,
    setups,
  };
  // Advanced fields: send only what was typed, so a blank box keeps the
  // server-side default instead of pinning today's default into the profile.
  const opt = {
    key_path: 'pt-tb-keypath',
    framework_path: 'pt-tb-framework',
    remote_workdir: 'pt-tb-workdir',
  };
  Object.entries(opt).forEach(([field, id]) => {
    const v = document.getElementById(id).value.trim();
    if (v) body[field] = v;
  });
  const pw = document.getElementById('pt-tb-password').value;
  if (pw) body.password = pw;

  const d = await ptApi('/profiles', { method: 'POST', body: JSON.stringify(body) }, ptStatusEl('pt-tb-status'));
  if (d) {
    document.getElementById('pt-tb-password').value = '';
    ptStatusEl('pt-tb-status').textContent = `Saved "${d.saved}" — press check on its row to verify SSH, framework and sudo.`;
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
  ptConfirm, ptSuggestStep, ptSuggestAllSteps, ptSearchStep,
  ptChooseMatches, ptClearChosen,
  ptGoStep, ptPrevStep, ptNextStep,
  ptSaveMatches,
  ptGatherFragments, ptSaveFragments, ptGenerateScript,
  ptFragGoStep, ptFragPrevStep, ptFragNextStep, ptFragToggle, ptPreviewFragments,
  ptLintScript, ptReviewScript, ptFixScript, ptFixFromSummary, ptSaveScript,
  ptLoadUnits, ptGenerateUnit, ptGenerateAllUnits, ptAssembleScript,
  ptGoUnit, ptGoSummary, ptUnitPrev, ptUnitNext, ptClearUnitErrors,
  ptViewSource, ptRun, ptValidate,
  ptEditProfile, ptSaveProfile, ptCheckProfile, ptResetProfileForm,
  ptAddSetupRow, ptRemoveSetupRow,
  ptCheckProfileNamed, ptDeleteProfile,
});
