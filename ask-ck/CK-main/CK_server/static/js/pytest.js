// PyTest Creator: the full 8-step gated flow.
import { registerActions } from './actions.js';
import { S } from './state.js';
import { dataArgs, escapeHtml } from './dom-helpers.js';
import { refreshCaseSelects } from './cases.js';
import { goToPanel } from './nav.js';
import { recordLLMDebug } from './llm-debug.js';

export let ptSession = null;          // server session for S.ptCase.key
let ptCaseInfo = null;         // {title, group_display, objective, steps} from load_case
let ptRunPoll = null;          // setInterval handle while a run is active

const PT_API = '/api/pytest-create';

async function ptApi(path, opts = {}, statusEl = null) {
  if (statusEl) statusEl.textContent = 'Working…';
  try {
    const r = await fetch(PT_API + path, Object.assign({
      headers: { 'Content-Type': 'application/json' },
    }, opts));
    const d = await r.json().catch(() => ({}));
    if (!r.ok) {
      const msg = d.detail || `HTTP ${r.status}`;
      if (statusEl) statusEl.textContent = '⚠ ' + msg;
      else alert('PyTest Creator: ' + msg);
      return null;
    }
    if (statusEl) statusEl.textContent = '';
    return d;
  } catch (e) {
    if (statusEl) statusEl.textContent = '⚠ ' + e;
    else alert('PyTest Creator: ' + e);
    return null;
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
  // refreshCaseSelects re-fetches /api/wizard/cases (which re-scans refined-cases)
  // and re-fills the PyTest Creator dropdown, preserving the current selection.
  await refreshCaseSelects(before);
  const sel = document.getElementById('ptCaseSelDone');
  // options include the placeholder, so count real cases
  const n = sel ? Array.from(sel.options).filter(o => o.value).length : 0;
  if (st) st.textContent = `Complete-case list refreshed — ${n} case(s). `
    + 'A case appears here only once it has a refined zephyr_payload.json (export it in the Objective/Test Case Generator first).';
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
  ptRenderSequence(((ptSession.step2 || {}).sequence) || []);
  const notes = (ptSession.step2 || {}).notes;
  if (notes) ptStatusEl('pt-seq-status').textContent = 'LLM notes: ' + notes;
  updatePtBadges();
}

function ptRenderSequence(seq) {
  const el = document.getElementById('pt-seq-list');
  if (!seq.length) {
    el.innerHTML = '<em class="review-empty">No sequence yet — run Extract Sequence (LLM).</em>';
    return;
  }
  let html = '<table class="table"><thead><tr><th style="width:24px">#</th><th>Action</th><th>Verify</th><th style="width:30px"></th></tr></thead><tbody>';
  seq.forEach((s, i) => {
    html += `<tr>
      <td>${i + 1}</td>
      <td><textarea class="form-input pt-seq-action" data-i="${i}" style="width:100%;height:44px;font-size:11px">${escapeHtml(s.action || '')}</textarea></td>
      <td><textarea class="form-input pt-seq-verify" data-i="${i}" style="width:100%;height:44px;font-size:11px">${escapeHtml(s.verify || '')}</textarea></td>
      <td><button class="btn btn-compact" data-action="ptRemoveSeqRow" data-args='[${i}]'>✕</button></td>
    </tr>`;
  });
  html += '</tbody></table><button class="btn btn-compact mt-2" data-action="ptAddSeqRow">+ Add step</button>';
  el.innerHTML = html;
}

function ptCollectSequence() {
  const actions = Array.from(document.querySelectorAll('.pt-seq-action'));
  const verifies = Array.from(document.querySelectorAll('.pt-seq-verify'));
  return actions.map((a, i) => ({
    n: i + 1, action: a.value.trim(), verify: (verifies[i] || {}).value ? verifies[i].value.trim() : '',
  })).filter(s => s.action);
}

function ptAddSeqRow() {
  const seq = ptCollectSequence();
  seq.push({ n: seq.length + 1, action: '', verify: '' });
  ptRenderSequence(seq);
}

function ptRemoveSeqRow(i) {
  const seq = ptCollectSequence();
  seq.splice(i, 1);
  ptRenderSequence(seq);
}

async function ptExtractSequence() {
  if (!ptRequireCase()) return;
  const btn = document.getElementById('pt-seq-extract-btn');
  btn.disabled = true;
  const d = await ptApi(`/extract_sequence/${S.ptCase.key}`, { method: 'POST' }, ptStatusEl('pt-seq-status'));
  btn.disabled = false;
  recordLLMDebug(btn);
  if (!d) return;
  await ptRefreshSession();
  ptRenderSequence(d.sequence || []);
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

// --- Step 3: Script Search --------------------------------------------------

export function renderPtSearchPanel() {
  if (!ptSession) { document.getElementById('pt-match-list').innerHTML = '<em class="review-empty">Load a case first.</em>'; return; }
  const st3 = ptSession.step3 || {};
  document.getElementById('pt-user-inputs').value = st3.user_inputs || '';
  ptRenderMatches(st3.matches || [], st3.selections || []);
  updatePtBadges();
}

function ptRenderMatches(matches, selections) {
  const el = document.getElementById('pt-match-list');
  if (!matches.length) {
    el.innerHTML = '<em class="review-empty">No matches yet — run Suggest from Sequence (LLM) or a free search.</em>';
    return;
  }
  const selSet = new Set(selections || []);
  // Group matches by source database so each shows in its own labeled, scrollable list.
  const DBS = [
    { key: 'art', label: 'testsuites_art' },
    { key: 'svt', label: 'svt_scripts' },
    { key: 'legacy', label: 'test_scripts' },
  ];
  const byDb = {};
  matches.forEach(m => { (byDb[m.db || 'other'] = byDb[m.db || 'other'] || []).push(m); });

  let html = `<div class="justification-note mb-1">${matches.length} match(es) across ${Object.keys(byDb).length} database(s)</div>`;
  const order = DBS.slice();
  // Any unexpected db bucket (shouldn't happen) appended at the end.
  Object.keys(byDb).forEach(k => { if (!order.some(d => d.key === k)) order.push({ key: k, label: k }); });

  order.forEach(({ key, label }) => {
    const group = byDb[key] || [];
    html += `<div class="pt-match-db"><div class="pt-match-db-head">${escapeHtml(label)} <span class="justification-note">(${group.length})</span></div>`;
    if (!group.length) {
      html += '<div class="justification-note pt-match-db-empty">No matches in this database.</div></div>';
      return;
    }
    html += '<div class="pt-match-scroll"><table class="table pt-match-table">'
      + '<thead><tr><th></th><th>Script</th><th>Coverage</th><th>Score</th><th>Why</th><th></th></tr></thead><tbody>';
    group.forEach(m => {
      const cov = m.coverage || '?';
      const covClass = cov === 'full' ? 'badge-success' : '';
      html += `<tr>
        <td><input type="checkbox" class="pt-match-sel" value="${escapeHtml(m.id)}" ${selSet.has(m.id) ? 'checked' : ''}></td>
        <td class="cell-id">${escapeHtml(m.id)}<div class="justification-note">${escapeHtml(m.title || '')}</div></td>
        <td><span class="badge ${covClass}">${escapeHtml(cov)}</span>${m.covers_steps && m.covers_steps.length ? `<div class="justification-note">steps ${m.covers_steps.join(',')}</div>` : ''}</td>
        <td>${m.score != null ? m.score : ''}</td>
        <td class="justification-note">${escapeHtml(m.reason || '')}</td>
        <td><button class="btn btn-compact" data-action="ptViewSource" data-args="${dataArgs(m.id)}">view</button></td>
      </tr>`;
    });
    html += '</tbody></table></div></div>';
  });
  el.innerHTML = html;
}

export async function ptManualSearch() {
  const q = document.getElementById('pt-search-q').value.trim();
  if (!q) return;
  const d = await ptApi(`/search_scripts?q=${encodeURIComponent(q)}&limit=25`, {}, ptStatusEl('pt-search-status'));
  if (!d) return;
  const cur = ((ptSession || {}).step3 || {}).selections || [];
  ptRenderMatches(d.results.map(r => ({ ...r, coverage: r.coverage || '?' })), cur);
  ptStatusEl('pt-search-status').textContent = `${d.results.length} index hits for "${q}" (free search — not persisted until you Save Selections).`;
}

async function ptSuggestScripts() {
  if (!ptRequireCase()) return;
  const btn = document.getElementById('pt-suggest-btn');
  btn.disabled = true;
  const d = await ptApi(`/suggest_scripts/${S.ptCase.key}`, {
    method: 'POST',
    body: JSON.stringify({ user_inputs: document.getElementById('pt-user-inputs').value }),
  }, ptStatusEl('pt-search-status'));
  btn.disabled = false;
  recordLLMDebug(btn);
  if (!d) return;
  await ptRefreshSession();
  ptRenderMatches(d.matches || [], ((ptSession || {}).step3 || {}).selections || []);
  ptStatusEl('pt-search-status').textContent =
    `${(d.matches || []).length} candidates (from ${d.mechanical_considered} mechanically scored). Tick the ones to carry into steps 4-5.`;
}

async function ptSaveMatches() {
  if (!ptRequireCase()) return;
  const sels = Array.from(document.querySelectorAll('.pt-match-sel:checked')).map(c => c.value);
  const d = await ptApi(`/save_matches/${S.ptCase.key}`, {
    method: 'POST',
    body: JSON.stringify({ selections: sels, user_inputs: document.getElementById('pt-user-inputs').value }),
  }, ptStatusEl('pt-search-status'));
  if (d) { await ptRefreshSession(); ptStatusEl('pt-search-status').textContent = `Saved ${sels.length} selection(s).`; }
}

async function ptViewSource(id) {
  const d = await ptApi(`/script_source?id=${encodeURIComponent(id)}&start=1&end=120`);
  if (!d) return;
  document.getElementById('pt-source-view').innerHTML =
    `<div class="justification-note">${escapeHtml(id)} (lines 1-120)</div><pre class="session-pre" style="max-height:300px;overflow:auto">${escapeHtml(d.source)}</pre>`;
}

// --- Step 4: Fit Decision ----------------------------------------------------

export function renderPtFitPanel() {
  const el = document.getElementById('pt-fit-result');
  if (!ptSession) { el.innerHTML = '<em class="review-empty">Load a case first.</em>'; return; }
  const s4 = ptSession.step4 || {};
  document.getElementById('pt-fit-decision').value = s4.decision || '';
  if (!s4.decision) { el.innerHTML = '<em class="review-empty">No assessment yet — run Assess Fit (LLM).</em>'; updatePtBadges(); return; }
  let html = `<div class="mb-2"><b>Decision:</b> <span class="badge">${escapeHtml(s4.decision)}</span>`
    + (s4.base_script ? ` base: <span class="cell-id">${escapeHtml(s4.base_script)}</span>` : '')
    + `</div><div class="justification-note mb-2">${escapeHtml(s4.rationale || '')}</div>`;
  const per = s4.per_step || [];
  if (per.length) {
    html += '<table class="table"><thead><tr><th style="width:24px">#</th><th>Covered by</th><th>Gap</th></tr></thead><tbody>';
    per.forEach(p => {
      html += `<tr><td>${p.n}</td><td class="cell-id">${escapeHtml(p.covered_by || '—')}</td><td class="justification-note">${escapeHtml(p.gap || '')}</td></tr>`;
    });
    html += '</tbody></table>';
  }
  el.innerHTML = html;
  updatePtBadges();
}

export function ptFitEdited() { /* decision select edited; persisted on Save */ }

async function ptAssessFit() {
  if (!ptRequireCase()) return;
  const btn = document.getElementById('pt-fit-btn');
  btn.disabled = true;
  const d = await ptApi(`/assess_fit/${S.ptCase.key}`, { method: 'POST' }, ptStatusEl('pt-fit-status'));
  btn.disabled = false;
  recordLLMDebug(btn);
  if (!d) return;
  await ptRefreshSession();
  renderPtFitPanel();
}

async function ptSaveFit() {
  if (!ptRequireCase()) return;
  const dec = document.getElementById('pt-fit-decision').value;
  if (!dec) { alert('Pick a decision first.'); return; }
  const s4 = ptSession.step4 || {};
  const d = await ptApi(`/save_fit/${S.ptCase.key}`, {
    method: 'POST',
    body: JSON.stringify({ decision: dec, base_script: s4.base_script || null }),
  }, ptStatusEl('pt-fit-status'));
  if (d) { await ptRefreshSession(); renderPtFitPanel(); ptStatusEl('pt-fit-status').textContent = 'Saved.'; }
}

// --- Step 5: Fragments --------------------------------------------------------

export function renderPtFragPanel() {
  const el = document.getElementById('pt-frag-list');
  if (!ptSession) { el.innerHTML = '<em class="review-empty">Load a case first.</em>'; return; }
  const frags = (ptSession.step5 || {}).fragments || [];
  if (!frags.length) {
    el.innerHTML = '<em class="review-empty">No fragments yet — run Gather Fragments (LLM). (A "new script from scratch" plan may legitimately keep this empty — Save then Confirm.)</em>';
    updatePtBadges();
    return;
  }
  let html = '';
  frags.forEach((f, i) => {
    html += `<div class="mb-2" style="border:1px solid var(--border-subtle);border-radius:4px;padding:6px">
      <label><input type="checkbox" class="pt-frag-keep" data-i="${i}" checked>
        <b>${escapeHtml(f.symbol)}</b> <span class="cell-id">from ${escapeHtml(f.source_id)}</span>
        <span class="justification-note">serves steps ${(f.maps_to || []).join(', ')}</span></label>
      <div class="justification-note">${escapeHtml(f.why || '')}</div>
      <details><summary class="justification-note">code (${(f.code || '').split('\n').length} lines)</summary>
        <pre class="session-pre" style="max-height:240px;overflow:auto">${escapeHtml(f.code || '')}</pre></details>
    </div>`;
  });
  el.innerHTML = html;
  updatePtBadges();
}

async function ptGatherFragments() {
  if (!ptRequireCase()) return;
  const btn = document.getElementById('pt-frag-btn');
  btn.disabled = true;
  const d = await ptApi(`/gather_fragments/${S.ptCase.key}`, { method: 'POST' }, ptStatusEl('pt-frag-status'));
  btn.disabled = false;
  recordLLMDebug(btn);
  if (!d) return;
  await ptRefreshSession();
  renderPtFragPanel();
  if (d.dropped) ptStatusEl('pt-frag-status').textContent = `${d.dropped} proposed fragment(s) failed symbol resolution and were dropped.`;
}

async function ptSaveFragments() {
  if (!ptRequireCase()) return;
  const frags = (ptSession.step5 || {}).fragments || [];
  const keep = Array.from(document.querySelectorAll('.pt-frag-keep:checked'))
    .map(c => frags[parseInt(c.dataset.i)])
    .filter(Boolean)
    .map(f => ({ source_id: f.source_id, symbol: f.symbol }));
  const d = await ptApi(`/save_fragments/${S.ptCase.key}`, {
    method: 'POST', body: JSON.stringify({ keep }),
  }, ptStatusEl('pt-frag-status'));
  if (d) { await ptRefreshSession(); renderPtFragPanel(); ptStatusEl('pt-frag-status').textContent = `Kept ${keep.length} fragment(s).`; }
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
  btn.disabled = true;
  ptStatusEl('pt-gen-status').textContent = 'Generating (this can take a few minutes)…';
  const d = await ptApi(`/generate_script/${S.ptCase.key}`, {
    method: 'POST',
    body: JSON.stringify({
      group: document.getElementById('pt-gen-group').value.trim(),
      name: document.getElementById('pt-gen-name').value.trim(),
    }),
  }, ptStatusEl('pt-gen-status'));
  btn.disabled = false;
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
  btn.disabled = true;
  ptStatusEl('pt-validate-status').textContent = 'Asking LLM for a fix (this can take a few minutes)…';
  const d = await ptApi(`/fix_script/${S.ptCase.key}`, { method: 'POST' }, ptStatusEl('pt-validate-status'));
  btn.disabled = false;
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
  ptConfirm, ptManualSearch, ptSuggestScripts,
  ptSaveMatches, ptAssessFit, ptSaveFit,
  ptGatherFragments, ptSaveFragments, ptGenerateScript,
  ptLintScript, ptFixScript, ptSaveScript,
  ptViewSource, ptRun, ptValidate,
  ptEditProfile, ptSaveProfile, ptCheckProfile,
  ptCheckProfileNamed, ptDeleteProfile,
});
