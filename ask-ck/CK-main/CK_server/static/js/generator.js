// Objective / Test Case Generator wizard.
import { registerActions } from './actions.js';
import { S } from './state.js';
import { escapeHtml, showStatus, setButtonBusy, flashButtonDone } from './dom-helpers.js';
import { renderChosenTable, renderStepTables } from './tables.js';
import { restoreChosenFromSelections, chosenSelections } from './chosen.js';
import { getActiveCaseKey, refreshCaseSelects, syncHiddenCaseSel } from './cases.js';
import { goToStep, updatePageHeader } from './nav.js';
import { normalizeLLMConfig, restoreLLMUI, updateLLMStatus } from './llm.js';
import { recordLLMDebug } from './llm-debug.js';
import { registerProvenance, renderProvenanceBlock, seedProvenanceFromStep } from './provenance.js';
import { onCaseLoaded, registerReloader } from './locks.js';

// Let "Take over" (locks.js) re-run the editable load without a circular import.
registerReloader('wizard', loadCase);

// --- Deferred per-step candidate loading -------------------------------------
// load_case deliberately returns no candidate pools: each review step fetches its
// own the first time you open it. Two separate incidents came from pre-loading data
// for panels the user had not visited (a ~60s LLM prefetch for Step 3, and a 2.7s
// 45k-row scan for Step 2 that ran bare on the event loop). See wizard.load_case.
// Declared above loadCase because loadCase resets the memo.
const _CANDIDATE_CONTAINERS = { 1: 'tl-table', 2: 'zephyr-table', 3: 'atp-table' };
const _STEP_BUS = { 1: 'currentTestLink', 2: 'currentZephyr', 3: 'currentATP' };
const _STEP_KIND = { 1: 'testlink', 2: 'zephyr', 3: 'atp' };

// `${key}:${step}` for pools already fetched, so revisiting a step is free and does
// not clobber rows the user merged in via Search / Suggest.
const _stepFetched = new Set();

async function loadCase() {
  const sel = getActiveCaseKey();
  if (!sel) {
    alert('Select a case from Open / partial or Complete first.');
    return;
  }
  S.currentKey = sel;
  syncHiddenCaseSel(sel);
  const loadBanner = document.getElementById('load-status');
  if (loadBanner) {
    loadBanner.classList.remove('hidden');
    loadBanner.textContent = `Loading ${sel}…`;
  }
  try {
    const res = await fetch(`/api/wizard/load_case/${sel}`, {method: 'POST'});
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`load_case failed (${res.status}): ${errText.slice(0, 200)}`);
    }
    const data = await res.json();
    S.currentSession = data.session;
    if (data.case_title) {
      window.currentCaseTitle = data.case_title;
    }
    updatePageHeader();

    // Candidate data buses (top tables); previously-confirmed selections restore
    // into the bottom "chosen" tables in insertion order (see chosen.js).
    const step1Sels = (S.currentSession.step1 && S.currentSession.step1.selections) || [];
    const step2Sels = (S.currentSession.step2 && S.currentSession.step2.selections) || [];
    const step3Sels = (S.currentSession.step3 && S.currentSession.step3.selections) || [];

    // Candidate pools are NOT part of the load response any more — each review step
    // fetches its own when you first open it (loadStepCandidates, called from
    // goToStep). Drop the previous case's pools so a stale row can never show under a
    // new case, and reset the fetch-once memo.
    window.currentTestLink = [];
    window.currentZephyr = [];
    window.currentATP = [];
    _stepFetched.clear();

    // Chosen lists DO come from the session, so they render immediately: a returning
    // user sees what they already picked without waiting for a candidate fetch.
    // Only the CHOSEN table is rendered here — deliberately not renderStepTables,
    // whose empty-candidate branch would print "No TestLink candidates for this
    // case.", asserting a fact we have not checked yet. Say "not fetched" instead.
    restoreChosenFromSelections('testlink', step1Sels);
    restoreChosenFromSelections('zephyr', step2Sels);
    restoreChosenFromSelections('atp', step3Sels);
    [1, 2, 3].forEach(step => {
      renderChosenTable(_STEP_KIND[step]);
      const cont = document.getElementById(_CANDIDATE_CONTAINERS[step]);
      if (cont) cont.innerHTML = '<em>Open this step to load candidates.</em>';
    });

    updateUI();
    // Session may include workspace LLM carried over from last Apply / Login
    restoreLLMUI();
    updateLLMStatus(normalizeLLMConfig(S.currentSession && S.currentSession.llm_config));

    // Restore synthesis views after reload
    renderObjectiveResult();
    renderStepsResult();
    renderReviewSummary();

    // Per-case lock (PLAN-auth-and-case-locking.md Phase 1). Do this AFTER the renders
    // so the read-only sweep catches every control they just added to the step panels.
    onCaseLoaded('wizard', sel, data.lock, data.read_only);
  } catch (e) {
    alert('Failed to load case: ' + e);
  } finally {
    if (loadBanner) loadBanner.classList.add('hidden');
    recordLLMDebug(null);   // load_case makes no LLM call; clear the panel footer
  }
}

export async function loadStepCandidates(step, { force = false } = {}) {
  const kind = _STEP_KIND[step];
  if (!kind || !S.currentKey) return;
  const bus = _STEP_BUS[step];
  const keyAtStart = S.currentKey;
  const memo = `${keyAtStart}:${step}`;
  if (!force && _stepFetched.has(memo)) return;

  const cont = document.getElementById(_CANDIDATE_CONTAINERS[step]);
  if (cont) cont.innerHTML = '<em>Loading candidates…</em>';
  try {
    const res = await fetch(
      `/api/wizard/step_candidates/${encodeURIComponent(keyAtStart)}/${step}`);
    if (!res.ok) throw new Error(`${res.status} ${(await res.text()).slice(0, 160)}`);
    const data = await res.json();

    // The user can act while this is in flight. Two races to lose gracefully:
    //  1. they loaded a DIFFERENT case  -> this response is stale, drop it entirely.
    //  2. they ran Search / Suggest on THIS step -> db-search.js merged rows into the
    //     same window bus. Those are an explicit request and outrank a default view,
    //     so do not overwrite them.
    if (S.currentKey !== keyAtStart) return;
    _stepFetched.add(memo);
    if ((window[bus] || []).length) return;

    window[bus] = data.candidates || [];
    renderStepTables(kind, window[bus]);
  } catch (e) {
    if (cont && S.currentKey === keyAtStart) {
      cont.innerHTML = '<em class="status-error">Could not load candidates — '
        + escapeHtml(String(e && e.message ? e.message : e))
        + '. Re-open this step to retry.</em>';
    }
  }
}

function updateUI() {
  document.getElementById('session-view').textContent = JSON.stringify(S.currentSession, null, 2);
  if (S.currentSession && S.currentSession.primary) {
    const p = S.currentSession.primary;
    const conf = p.c ? ` <span class="badge">${escapeHtml(String(p.c))}</span>` : '';
    const why = p.w ? ` <span class="justification-note">— ${escapeHtml(String(p.w))}</span>` : '';
    document.getElementById('primary').innerHTML = `<b>Primary:</b> <span class="sel-label">${escapeHtml(p.m || 'None')}</span>${conf}${why}`;
  }
  const s = S.currentSession || {};
  updateLLMStatus();
  renderReviewSummary();

  // Confirmed badges on step headings + sidebar nav
  [1, 2, 3].forEach(step => {
    const conf = !!(s['step' + step] && s['step' + step].confirmed);
    const badge = document.getElementById('step' + step + '-badge');
    if (badge) {
      badge.classList.toggle('hidden', !conf);
      badge.className = conf ? 'badge badge-success' : 'badge hidden';
      badge.textContent = conf ? '✓ Confirmed' : '';
    }
  });
  // Step 4 objectives / Step 5 steps badges.
  // `stale` is set server-side by _invalidate_downstream when an upstream DB review
  // (steps 1-3) is re-confirmed with DIFFERENT selections: the generated content is
  // kept but no longer matches what it was synthesized from. Showing it as Confirmed/
  // Ready there is what let a contradictory bundle reach export, so stale outranks both.
  const hasObj = !!(s.step4 && (s.step4.objective || '').trim());
  const objStale = !!(s.step4 && s.step4.stale && hasObj);
  const objConf = !!(s.step4 && s.step4.confirmed && hasObj && !objStale);
  const badge4 = document.getElementById('step4-badge');
  if (badge4) {
    if (objStale) {
      badge4.className = 'badge badge-warning';
      badge4.textContent = '⚠ Stale — selections changed';
      badge4.classList.remove('hidden');
    } else if (objConf) {
      badge4.className = 'badge badge-success';
      badge4.textContent = '✓ Confirmed';
      badge4.classList.remove('hidden');
    } else if (hasObj) {
      badge4.className = 'badge';
      badge4.textContent = 'Draft';
      badge4.classList.remove('hidden');
    } else {
      badge4.classList.add('hidden');
    }
  }
  const steps = getSessionTestScript(s);
  const hasSteps = !!(steps && steps.steps && steps.steps.length);
  const stepsStale = !!(s.step5 && s.step5.stale && hasSteps);
  const badge5 = document.getElementById('step5-badge');
  if (badge5) {
    if (stepsStale) {
      badge5.className = 'badge badge-warning';
      badge5.textContent = '⚠ Stale — selections changed';
      badge5.classList.remove('hidden');
    } else if (hasSteps) {
      badge5.className = 'badge badge-success';
      badge5.textContent = '✓ Ready';
      badge5.classList.remove('hidden');
    } else {
      badge5.classList.add('hidden');
    }
  }

  // Scoped to the Generator section: ✓ nav-badges must never attach to other tools' items
  document.querySelectorAll('#nav-generator .sidebar-nav-item[data-step]').forEach(item => {
    const step = parseInt(item.getAttribute('data-step'));
    let conf = false;
    if (step === 1) conf = !!(s.step1 && s.step1.confirmed);
    if (step === 2) conf = !!(s.step2 && s.step2.confirmed);
    if (step === 3) conf = !!(s.step3 && s.step3.confirmed);
    if (step === 4) conf = objConf;
    if (step === 5) conf = hasSteps;
    let b = item.querySelector('.nav-badge');
    if (conf && !b) {
      b = document.createElement('span');
      b.className = 'nav-badge badge badge-success';
      b.textContent = '✓';
      item.appendChild(b);
    } else if (!conf && b) {
      b.remove();
    }
  });

  renderObjectiveResult();
  renderStepsResult();
}
function getSessionTestScript(sess) {
  const s = sess || S.currentSession || {};
  if (s.step5 && s.step5.testScript) return s.step5.testScript;
  if (s.step4 && s.step4.testScript) return s.step4.testScript;
  return { type: 'steps', steps: [] };
}

function getSessionObjective(sess) {
  const s = sess || S.currentSession || {};
  return ((s.step4 && s.step4.objective) || '').trim();
}

export function renderObjectiveResult() {
  const container = document.getElementById('objective-result');
  if (!container) return;
  const obj = getSessionObjective();
  if (!obj) {
    container.innerHTML = '<em class="review-empty">No objective yet. Confirm steps 2–4, then click Synthesize Objectives.</em>';
    return;
  }
  const conf = !!(S.currentSession && S.currentSession.step4 && S.currentSession.step4.confirmed);
  const prov = (S.currentSession && S.currentSession.step4 && S.currentSession.step4.provenance) || null;
  const caseKey = (S.currentSession && S.currentSession.key) || '';
  registerProvenance('panel-objectives',
    () => '/api/wizard/synthesize_objectives',
    () => ({ session: S.currentSession }));
  if (prov) seedProvenanceFromStep('panel-objectives', prov);
  const provenanceHtml = renderProvenanceBlock('panel-objectives');
  container.innerHTML = `
    <div class="section">
      <div class="section-heading">Objective (Human-Readable)
        ${conf ? '<span class="badge badge-success">✓ Confirmed</span>' : '<span class="badge">Draft — confirm when ready</span>'}
      </div>
      <div class="synth-objective" id="synth-objective-view">${obj}</div>
    </div>
    <div class="synth-actions" id="objective-edit-actions">
      <button type="button" data-action="startEditObjective" class="btn btn-secondary">Edit Objective</button>
    </div>
    ${provenanceHtml}
  `;
  // Keep Step 5 preview in sync
  const prev = document.getElementById('finalized-objective-content');
  if (prev) prev.innerHTML = obj;
}

export function renderStepsResult() {
  const container = document.getElementById('steps-result');
  if (!container) return;
  const ts = getSessionTestScript();
  const steps = (ts && ts.steps) || [];
  if (!steps.length) {
    container.innerHTML = '<em class="review-empty">No test steps yet. Confirm objectives in Step 5, then Synthesize Test Steps.</em>';
    return;
  }
  let stepsHtml = '<ol class="synth-steps">';
  steps.forEach((s) => {
    const desc = escapeHtml(s.description || '');
    const exp = s.expectedResult ? `<div class="step-expected"><em>Expected:</em> ${escapeHtml(s.expectedResult)}</div>` : '';
    stepsHtml += `<li><div>${desc}</div>${exp}</li>`;
  });
  stepsHtml += '</ol>';
  const prov = (S.currentSession && S.currentSession.step5 && S.currentSession.step5.provenance)
    || (S.currentSession && S.currentSession.step4 && S.currentSession.step4.provenance)
    || null;
  registerProvenance('panel-steps',
    () => '/api/wizard/synthesize_steps',
    () => ({ session: S.currentSession }));
  if (prov && (prov.steps_prompt || prov.phase === 'steps' || prov.phase === 'combined')) {
    seedProvenanceFromStep('panel-steps', prov);
  }
  const provenanceHtml = renderProvenanceBlock('panel-steps');
  container.innerHTML = `
    <div class="section">
      <div class="section-heading">Test Steps (Human-Readable)</div>
      <div id="synth-steps-view">${stepsHtml}</div>
    </div>
    <div class="synth-actions" id="steps-edit-actions"></div>
    <div class="synth-actions" id="steps-export-actions">
      <button type="button" data-action="exportBundle" class="btn btn-export">Export Repeatable Bundle</button>
      <button type="button" data-action="pushToZephyr" data-args='[false]' class="btn btn-secondary">Preview Push (dry-run)</button>
      <button type="button" data-action="pushToZephyr" data-args='[true]' class="btn btn-primary">Push to Zephyr</button>
    </div>
    <div class="justification-note mt-2">Push uses the <strong>last exported bundle on disk</strong> (click <em>Export Repeatable Bundle</em> first if you've made edits). On the live Zephyr case it strips a leading <code>(N)</code> title group, ensures version 2.0, and uploads the objective + steps + traceability onto it. Run <em>Preview</em> first.</div>
    <pre id="push-zephyr-output" class="push-output" style="display:none;"></pre>
    ${provenanceHtml}
  `;
  const prev = document.getElementById('finalized-objective-content');
  if (prev) {
    const obj = getSessionObjective();
    prev.innerHTML = obj || '<em class="review-empty">No objective on session.</em>';
  }
}

// --- Step 4 objective editor ---
let _editingObjective = false;

function startEditObjective() {
  if (!S.currentSession) return;
  _editingObjective = true;
  const objView = document.getElementById('synth-objective-view');
  if (!objView) return;
  const objHtml = getSessionObjective();
  objView.innerHTML = `<textarea id="edit-objective" class="form-textarea full-width editor-textarea" spellcheck="false">${escapeHtml(objHtml)}</textarea>
    <div class="justification-note mt-2">Edit the objective HTML (<code>&lt;ul&gt;&lt;li&gt;…</code> artefacts). Keep declarative language.</div>`;
  const actions = document.getElementById('objective-edit-actions');
  if (actions) {
    actions.innerHTML = `
      <button type="button" data-action="applyObjectiveEdits" data-args='[false]' class="btn btn-primary">Save Draft</button>
      <button type="button" data-action="applyObjectiveEdits" data-args='[true]' class="btn btn-primary">Save &amp; Confirm → Step 6</button>
      <button type="button" data-action="cancelObjectiveEdits" class="btn btn-secondary">Cancel</button>
    `;
  }
}

async function applyObjectiveEdits(alsoConfirm) {
  if (!S.currentSession || !S.currentKey) return;
  const objTa = document.getElementById('edit-objective');
  const objective = objTa ? objTa.value.trim() : getSessionObjective();
  if (!objective) {
    alert('Objective cannot be empty.');
    return;
  }
  try {
    const res = await fetch('/api/wizard/save_objective/' + encodeURIComponent(S.currentKey), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ objective, confirm: !!alsoConfirm }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    S.currentSession = data.session;
    _editingObjective = false;
    renderObjectiveResult();
    updateUI();
    if (alsoConfirm) {
      goToStep(5);
    }
  } catch (e) {
    alert('Save objective failed: ' + e);
  }
}

function cancelObjectiveEdits() {
  _editingObjective = false;
  renderObjectiveResult();
}

async function confirmObjectives() {
  if (!S.currentKey) return alert('Load a case first.');
  // Capture any in-progress textarea
  const objTa = document.getElementById('edit-objective');
  const body = {};
  if (objTa) body.objective = objTa.value.trim();
  try {
    const res = await fetch('/api/wizard/confirm_objectives/' + encodeURIComponent(S.currentKey), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    S.currentSession = data.session;
    _editingObjective = false;
    updateUI();
    goToStep(5);
  } catch (e) {
    alert('Confirm objectives failed: ' + e);
  }
}

// --- Step 5 steps editor ---
let _editingSteps = null;

function startEditSteps() {
  if (!S.currentSession) return;
  const ts = getSessionTestScript();
  const steps = (ts && ts.steps) || [];
  if (!steps.length) {
    alert('No test steps to edit yet. Synthesize Test Steps first.');
    return;
  }
  _editingSteps = JSON.parse(JSON.stringify(ts || { type: 'steps', steps: [] }));
  if (!_editingSteps.steps) _editingSteps.steps = [];
  renderEditStepsList();
  const actions = document.getElementById('steps-edit-actions');
  if (actions) {
    actions.innerHTML = `
      <button type="button" data-action="applyStepEdits" class="btn btn-primary">Apply Step Edits</button>
      <button type="button" data-action="cancelStepEdits" class="btn btn-secondary">Cancel</button>
      <button type="button" data-action="addSynthesizedStep" class="btn btn-ghost btn-compact-small">+ Add step</button>
    `;
  }
}

function renderEditStepsList() {
  const stepsView = document.getElementById('synth-steps-view');
  if (!stepsView || !_editingSteps) return;
  const steps = _editingSteps.steps || [];
  let editSteps = '<div class="editable-steps">';
  steps.forEach((s, idx) => {
    const desc = escapeHtml(s.description || '');
    const exp = escapeHtml(s.expectedResult || '');
    editSteps += `
      <div class="editable-step" data-idx="${idx}">
        <div class="editable-step-num">${idx + 1}.</div>
        <div class="editable-step-fields">
          <input data-field="description" data-idx="${idx}" value="${desc}" class="form-input" placeholder="Step description" />
          <input data-field="expectedResult" data-idx="${idx}" value="${exp}" class="form-input" placeholder="Expected result (optional)" />
          <div class="editor-toolbar">
            <button type="button" class="btn btn-ghost btn-compact-small" data-action="removeSynthesizedStep" data-args='[${idx}]'>Remove</button>
          </div>
        </div>
      </div>`;
  });
  editSteps += '</div>';
  stepsView.innerHTML = editSteps;
}

function addSynthesizedStep() {
  if (!_editingSteps) return;
  if (!_editingSteps.steps) _editingSteps.steps = [];
  _editingSteps.steps.push({ description: '', expectedResult: '' });
  renderEditStepsList();
}

function removeSynthesizedStep(idx) {
  if (!_editingSteps) return;
  _editingSteps.steps.splice(idx, 1);
  renderEditStepsList();
}

async function applyStepEdits() {
  if (!_editingSteps || !S.currentSession || !S.currentKey) return;
  document.querySelectorAll('#synth-steps-view .editable-step input').forEach(inp => {
    const idx = parseInt(inp.getAttribute('data-idx'), 10);
    const field = inp.getAttribute('data-field') || 'description';
    if (_editingSteps.steps[idx]) {
      _editingSteps.steps[idx][field] = inp.value.trim();
    }
  });
  try {
    const res = await fetch('/api/wizard/save_steps/' + encodeURIComponent(S.currentKey), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ testScript: { type: 'steps', steps: _editingSteps.steps } }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    S.currentSession = data.session;
    _editingSteps = null;
    renderStepsResult();
    updateUI();
  } catch (e) {
    alert('Save steps failed: ' + e);
  }
}

function cancelStepEdits() {
  _editingSteps = null;
  renderStepsResult();
}

export function renderReviewSummary() {
  const cont = document.getElementById('review-summary-content');
  if (!cont) return;
  if (!S.currentSession) {
    cont.innerHTML = '<em class="review-empty">Load a case and confirm steps 2–4 to see selection previews.</em>';
    return;
  }

  const s1 = S.currentSession.step1 || {};
  const s2 = S.currentSession.step2 || {};
  const s3 = S.currentSession.step3 || {};

  function renderStepGroup(label, sels, confirmed, idKey) {
    const list = sels || [];
    const confBadge = confirmed
      ? ' <span class="badge badge-success">✓ Confirmed</span>'
      : ' <span class="badge">Pending</span>';
    const count = `<span class="review-count">(${list.length} selected)</span>`;
    if (!list.length) {
      return `<div class="sel-group"><strong>${label}:</strong>${confBadge}${count} <span class="review-empty">— none yet</span></div>`;
    }
    let html = `<div class="sel-group"><strong>${label}:</strong>${confBadge}${count}`;
    list.forEach((sel, i) => {
      if (i >= 5) return;
      const id = sel[idKey] || sel.id_or_key || sel.key || '';
      const title = sel.title ? ` ${escapeHtml(sel.title)}` : '';
      let just = sel.justification || '';
      if (just.length > 80) just = just.slice(0, 77) + '…';
      const justHtml = just ? ` <span class="justification-note">(${escapeHtml(just)})</span>` : '';
      html += `<div class="sel-item"><span class="sel-label">${escapeHtml(id)}</span>${title}${justHtml}</div>`;
    });
    if (list.length > 5) {
      html += `<div class="review-empty">+${list.length - 5} more</div>`;
    }
    html += `</div>`;
    return html;
  }

  let html = '';
  html += renderStepGroup('Step 2 (TestLink)', s1.selections, s1.confirmed, 'id_or_key');
  html += renderStepGroup('Step 3 (Zephyr)', s2.selections, s2.confirmed, 'id_or_key');
  html += renderStepGroup('Step 4 (ATPyLib)', s3.selections, s3.confirmed, 'id_or_key');

  // Gaps stay in traceability.md only — not shown in the wizard Step 4 UI.

  const obj = getSessionObjective(S.currentSession);
  if (obj) {
    const conf = !!(S.currentSession.step4 && S.currentSession.step4.confirmed);
    const confBadge = conf
      ? ' <span class="badge badge-success">✓ Confirmed</span>'
      : ' <span class="badge">Draft</span>';
    const shortObj = obj.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    const preview = shortObj.length > 160 ? shortObj.slice(0, 157) + '…' : shortObj;
    html += `<div class="sel-group"><strong>Step 5 (Objective)</strong>${confBadge}: <span class="justification-note">${escapeHtml(preview)}</span></div>`;
  }

  cont.innerHTML = html;
}
async function confirmStep(step) {
  if (!S.currentKey) return alert('Load a case first');

  // Confirm reads ONLY the bottom "chosen" table for each step (not the top
  // candidates). See chosen.js.
  let body = {};
  if (step === 1) body = { selections: chosenSelections('testlink') };
  else if (step === 2) body = { selections: chosenSelections('zephyr') };
  else if (step === 3) body = { selections: chosenSelections('atp') };

  let data;
  try {
    const res = await fetch(`/api/wizard/confirm_step/${encodeURIComponent(S.currentKey)}/${step}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    // Without this check an error response was assigned straight into state:
    // `S.currentSession = data.session` set it to undefined, silently wiping the
    // in-memory session while the UI carried on as if the confirm had worked.
    data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || ('HTTP ' + res.status));
  } catch (e) {
    alert(`Confirm failed: ${e.message || e}`);
    return;
  }
  // Only adopt a payload that actually carries a session, so a malformed 200 cannot
  // clobber it either.
  if (data && data.session) S.currentSession = data.session;
  updateUI();
  // Batch A: confirming with CHANGED selections invalidates the downstream objective
  // and steps. Say so — otherwise the badges flip to "Stale" with no explanation.
  const inv = data && data.invalidated;
  if (inv && (inv.step4 || inv.step5)) {
    alert('Selections changed — the objective and test steps no longer match them.\n'
        + 'They are kept but marked Stale; re-synthesize or re-confirm them.');
  } else if (data && data.can_synthesize) {
    alert('All reviews confirmed. Go to Step 5 (Objective Synthesis).');
  }
}

async function synthesizeObjectives() {
  if (!S.currentSession) return alert('Load a case and confirm steps 2–4 first.');
  const btn = document.getElementById('obj-synth-btn');
  if (!setButtonBusy(btn, true, { label: 'Synthesizing…' })) return;   // guard double-click
  showStatus('objective-status', 'busy', 'Synthesizing objectives (LLM)… this can take a while on the Thinking model.');
  let ok = false;
  try {
    const res = await fetch('/api/wizard/synthesize_objectives', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session: S.currentSession, use_llm: true }),
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(t.slice(0, 300) || ('status ' + res.status));
    }
    const data = await res.json();
    S.currentSession = data.session;
    showStatus('objective-status', 'clear');
    renderObjectiveResult();
    updateUI();
    goToStep(4);
    ok = true;
  } catch (e) {
    showStatus('objective-status', 'error', 'Objective synthesis failed: ' + e);
  } finally {
    setButtonBusy(btn, false);
    flashButtonDone(btn, ok);
    recordLLMDebug(btn);
  }
}

async function synthesizeSteps() {
  if (!S.currentSession) return alert('Load a case first.');
  if (!getSessionObjective()) {
    alert('No objective yet. Complete Step 5 (Objective Synthesis) and confirm first.');
    goToStep(4);
    return;
  }
  const btn = document.getElementById('steps-synth-btn');
  if (!setButtonBusy(btn, true, { label: 'Synthesizing…' })) return;   // guard double-click
  showStatus('steps-status', 'busy', 'Synthesizing test steps (LLM)… this can take a while on the Thinking model.');
  let ok = false;
  try {
    const res = await fetch('/api/wizard/synthesize_steps', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session: S.currentSession, use_llm: true }),
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(t.slice(0, 300) || ('status ' + res.status));
    }
    const data = await res.json();
    S.currentSession = data.session;
    const synth = data.synthesized || {};
    const v = synth.validation || {};
    if (v.valid === false) {
      showStatus('steps-status', 'warning',
        'Steps synthesized, but validation flagged issues to review before export:',
        (v.issues && v.issues.length) ? v.issues : ['validation failed']);
    } else {
      showStatus('steps-status', 'clear');
    }
    renderStepsResult();
    updateUI();
    goToStep(5);
    ok = true;
  } catch (e) {
    showStatus('steps-status', 'error', 'Test step synthesis failed: ' + e);
  } finally {
    setButtonBusy(btn, false);
    flashButtonDone(btn, ok);
    recordLLMDebug(btn);
  }
}

/** @deprecated Use synthesizeObjectives / synthesizeSteps */
export async function synthesize() {
  return synthesizeObjectives();
}

async function exportBundle() {
  if (!S.currentSession) return;
  const btn = this instanceof HTMLElement ? this : null;   // clicked Export button
  if (!setButtonBusy(btn, true, { label: 'Exporting…' })) return;   // guard double-click
  showStatus('export-status', 'busy', 'Exporting… (rendering bundle + coverage gaps)');
  let ok = false;
  try {
    const res = await fetch('/api/wizard/export', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({session: S.currentSession})
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(t.slice(0, 300) || ('status ' + res.status));
    }
    const data = await res.json();
    const v = data.validation || {};

    // Backend now REFUSES to write the drop-in bundle when hard validation issues exist
    // (a broken bundle must not silently promote a case to Complete). Use the server's
    // message as the headline — it is stale-bundle-aware (a case exported before is STILL
    // Complete on disk even though THIS export wrote nothing), so we must not hard-code
    // "NOT Complete" here. Show the issues list below it. Do NOT refresh the dropdown.
    if (data.wrote_bundle === false) {
      const headline = data.message
        ? data.message.split('\n')[0]
        : 'Export blocked — no bundle written.';
      showStatus('export-status', 'error', headline,
        (v.issues && v.issues.length) ? v.issues : ['validation failed']);
      return;
    }

    const savedTo = data.saved_to || ('refined-cases/<Group>/' + (S.currentKey || 'case'));
    const files = (data.saved_files && data.saved_files.length)
      ? data.saved_files.join(', ')
      : 'traceability.md, zephyr_payload.json, ' + (S.currentKey || 'case') + '-session.json';

    // Wrote successfully. Advisory warnings (if any) shown as a warning banner, else success.
    const warnings = (v.warnings && v.warnings.length) ? v.warnings : null;
    showStatus('export-status', warnings ? 'warning' : 'success',
      'Export complete — saved on the server at ' + savedTo + '/ (' + files + '). '
      + 'Drop-in for refined-cases + upload tooling.'
      + (warnings ? ' Advisory warnings:' : ''),
      warnings);

    ok = true;
    // Case may have moved into Complete — refresh dual dropdowns
    try { await refreshCaseSelects(S.currentKey); } catch (_) {}
  } catch (e) {
    showStatus('export-status', 'error', 'Export failed: ' + e);
  } finally {
    setButtonBusy(btn, false);
    flashButtonDone(btn, ok);
    recordLLMDebug(null);   // export synthesizes coverage-gaps (LLM) — footer only
  }
}

// Push the current Complete case to Zephyr (title fix + new version + payload)
// by asking the server to shell out to tool/upload_refined.py. `execute=false`
// runs a dry-run preview (no writes); `execute=true` performs the real push.
async function pushToZephyr(execute) {
  const key = S.currentKey || getActiveCaseKey();
  if (!key) return alert('No case loaded. Load a Complete case first.');

  if (execute) {
    const ok = confirm(
      `Push ${key} to the LIVE Zephyr server?\n\n`
      + 'This will:\n'
      + '  1. Strip a leading "(N)" group from the test-case title\n'
      + '  2. Create a NEW version (e.g. 1.0 → 2.0)\n'
      + '  3. Upload the objective + test steps onto the new version\n'
      + '  4. Attach traceability.md + web links\n\n'
      + 'Tip: run "Preview Push (dry-run)" first. Continue?'
    );
    if (!ok) return;
  }

  const out = document.getElementById('push-zephyr-output');
  if (out) {
    out.style.display = 'block';
    out.textContent = execute ? 'Pushing to Zephyr…' : 'Previewing (dry-run, no writes)…';
  }

  try {
    // NOTE: intentionally NO export-first here. Push operates on the canonical
    // on-disk refined-case bundle (traceability.md + zephyr_payload.json). Re-
    // exporting from the live session would DEGRADE those artefacts for any case
    // whose session is incomplete (e.g. a Complete case rehydrated via backfill
    // that carries only step4/step5, not the step1–3 selections). If you edited
    // the objective/steps, click "Export Repeatable Bundle" first, then Push.
    // A real push carries a per-case confirmation token in the body. dry_run is a
    // query param, so without this a production write is one character from a
    // preview for any non-browser client. Only the execute path sends it.
    const res = await fetch(
      `/api/wizard/push_to_zephyr/${encodeURIComponent(key)}?dry_run=${execute ? 'false' : 'true'}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(execute ? { confirm: key } : {}),
      }
    );
    const data = await res.json().catch(() => ({}));
    const body = (data && data.output) ? data.output
      : (data && data.detail) ? data.detail
      : `HTTP ${res.status}`;
    const header = (data && data.ok === false)
      ? `⚠ Push ${execute ? 'FAILED' : 'preview reported problems'} (exit ${data.returncode}) — check JIRA_KEY in secrets.md and output below:\n\n`
      : !res.ok
        ? `⚠ Push refused (HTTP ${res.status}):\n\n`
        : (execute ? '✓ Push complete:\n\n' : 'Dry-run preview (no changes made):\n\n');
    if (out) out.textContent = header + body;
  } catch (e) {
    if (out) out.textContent = 'Push failed: ' + e;
  } finally {
    recordLLMDebug(null);   // no LLM call in this path — clear the footer
  }
}

async function clearCurrentSession() {
  if (!S.currentKey) S.currentKey = getActiveCaseKey();
  if (!S.currentKey) return alert('No case selected');

  if (!confirm(`Clear case session for ${S.currentKey}?\nSelections / confirms / synthesis for this case will be reset.\nYour workspace LLM preference (CLI login) is kept.`)) {
    return;
  }

  try {
    const res = await fetch(`/api/wizard/clear_session/${S.currentKey}`, { method: 'POST' });
    if (res.ok) {
      alert('Case session cleared. Workspace LLM preference is kept.');
      // Reset case state only (LLM preference is workspace-scoped)
      S.currentSession = null;

      // Clear rendered tables/content for the steps
      const tables = ['tl-table', 'zephyr-table', 'atp-table'];
      tables.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = '<em>Select and Load a case to see data.</em>';
      });
      const synth = document.getElementById('objective-result');
      if (synth) synth.innerHTML = '';
      const stepsEl = document.getElementById('steps-result');
      if (stepsEl) stepsEl.innerHTML = '';
      const _legacySynth = document.getElementById('synth-result');
      if (synth) synth.innerHTML = '';

      // Re-load case; server re-applies workspace LLM default
      await loadCase();
    } else {
      alert('Failed to clear session.');
    }
  } catch (e) {
    alert('Error clearing session: ' + e);
  }
}


// Register this tool's data-action handlers.
registerActions({
  loadCase, confirmStep, clearCurrentSession, pushToZephyr,
  exportBundle, synthesizeObjectives, startEditObjective,
  applyObjectiveEdits, cancelObjectiveEdits, confirmObjectives,
  synthesizeSteps, startEditSteps, applyStepEdits,
  cancelStepEdits, addSynthesizedStep, removeSynthesizedStep,
});
