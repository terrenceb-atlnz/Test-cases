// ============================================================================
// Per-tab session id + X-CK-Session header injection.
// Each browser tab gets a unique id so the shared server can route claude_agent
// LLM jobs back to THIS user's browser (and thus their own local ck-agent).
// We patch window.fetch once so every same-origin /api call carries the header
// without touching each call site.
// ============================================================================
const CK_SESSION_ID = (function () {
  let id = sessionStorage.getItem('ckSessionId');
  if (!id) {
    id = 'sess-' + Math.random().toString(36).slice(2) + '-' + Date.now().toString(36);
    sessionStorage.setItem('ckSessionId', id);
  }
  return id;
})();
(function patchFetch() {
  const orig = window.fetch;
  window.fetch = function (input, init) {
    try {
      const url = (typeof input === 'string') ? input : (input && input.url) || '';
      // Only attach to our own API (never to the localhost agent or external hosts).
      const sameApi = url.startsWith('/api/') || url.includes(location.host + '/api/');
      if (sameApi) {
        init = init || {};
        const headers = new Headers(init.headers || (typeof input !== 'string' && input.headers) || {});
        headers.set('X-CK-Session', CK_SESSION_ID);
        init.headers = headers;
      }
    } catch (_) { /* never break fetch */ }
    return orig.call(this, input, init);
  };
})();

let currentSession = null;
let currentKey = null;
let currentStep = 0;
let currentPanel = 'step-0';
// PyTest Creator selection — deliberately separate from currentKey (the Generator's loaded case)
let ptCase = { key: null, title: null };

async function loadCase() {
  const sel = getActiveCaseKey();
  if (!sel) {
    alert('Select a case from Open / partial or Complete first.');
    return;
  }
  currentKey = sel;
  syncHiddenCaseSel(sel);
  const loadBanner = document.getElementById('load-status');
  if (loadBanner) {
    loadBanner.classList.remove('hidden');
    loadBanner.textContent = `Loading ${sel}… (data + related Zephyr + ATP)`;
  }
  try {
    const res = await fetch(`/api/wizard/load_case/${sel}`, {method: 'POST'});
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`load_case failed (${res.status}): ${errText.slice(0, 200)}`);
    }
    const data = await res.json();
    currentSession = data.session;
    if (data.case_title) {
      window.currentCaseTitle = data.case_title;
    }
    updatePageHeader();

    // Hook up real data tables, restoring any previously confirmed selections from session
    const step1Sels = (currentSession.step1 && currentSession.step1.selections) || [];
    const step2Sels = (currentSession.step2 && currentSession.step2.selections) || [];
    const step3Sels = (currentSession.step3 && currentSession.step3.selections) || [];

    if (data.testlink_candidates) {
      window.currentTestLink = data.testlink_candidates;
      renderTestLinkTable(data.testlink_candidates, step1Sels);
    }
    if (data.zephyr_refs) {
      window.currentZephyr = data.zephyr_refs;
      renderZephyrTable(data.zephyr_refs, step2Sels);
    }
    if (data.atp_candidates) {
      window.currentATP = data.atp_candidates;
      renderATPTable(data.atp_candidates, step3Sels);
    }
    updateUI();
    // Session may include workspace LLM carried over from last Apply / Login
    restoreLLMUI();
    updateLLMStatus(normalizeLLMConfig(currentSession && currentSession.llm_config));

    // Handle Step 3 restoration (now uses pre-loaded scored table)
    if (step3Sels.length > 0) {
      setTimeout(() => {
        step3Sels.forEach(s => {
          const cb = document.querySelector(`#atp-table input.atp-checkbox[data-id="${s.id_or_key}"]`);
          if (cb) cb.checked = true;
        });
      }, 300);
    }

    // Restore synthesis views after reload
    renderObjectiveResult();
    renderStepsResult();
    renderReviewSummary();
  } catch (e) {
    alert('Failed to load case: ' + e);
  } finally {
    if (loadBanner) loadBanner.classList.add('hidden');
  }
}

function updateUI() {
  document.getElementById('session-view').textContent = JSON.stringify(currentSession, null, 2);
  if (currentSession && currentSession.primary) {
    const p = currentSession.primary;
    const conf = p.c ? ` <span class="badge">${escapeHtml(String(p.c))}</span>` : '';
    const why = p.w ? ` <span class="justification-note">— ${escapeHtml(String(p.w))}</span>` : '';
    document.getElementById('primary').innerHTML = `<b>Primary:</b> <span class="sel-label">${escapeHtml(p.m || 'None')}</span>${conf}${why}`;
  }
  const s = currentSession || {};
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
  // Step 4 objectives / Step 5 steps badges
  const hasObj = !!(s.step4 && (s.step4.objective || '').trim());
  const objConf = !!(s.step4 && s.step4.confirmed && hasObj);
  const badge4 = document.getElementById('step4-badge');
  if (badge4) {
    if (objConf) {
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
  const badge5 = document.getElementById('step5-badge');
  if (badge5) {
    if (hasSteps) {
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

// Soft safety only for pathological megabyte fields (real TL/Zephyr bodies are typically < few KB)
const DESC_SOFT_MAX = 2000;

// Render real selectable tables for steps
function renderTestLinkTable(cands, existingSelections = []) {
  const cont = document.getElementById('tl-table');
  if (!cands || cands.length === 0) {
    cont.innerHTML = '<em>No TestLink candidates for this case.</em>';
    return;
  }
  // Build lookup for saved selections (justification is optional note, not a substitute for full body)
  const saved = {};
  existingSelections.forEach(s => { saved[s.id_or_key] = s.justification || ''; });

  let html = '<table class="table cols-5"><thead><tr><th></th><th>ID</th><th>Title</th><th>Score</th><th>Description</th></tr></thead><tbody>';
  cands.forEach((c, idx) => {
    const hasSaved = Object.keys(saved).length > 0;
    const isChecked = saved.hasOwnProperty(c.id) || (!hasSaved && idx < 3);
    // Prefer full source description; only fall back to saved justification if body is empty
    let descValue = c.description || c.snippet || c.title || '';
    if ((!descValue || descValue.length < 40) && saved[c.id]) {
      descValue = saved[c.id];
    }
    descValue = truncateText(descValue, DESC_SOFT_MAX);
    const checkedAttr = isChecked ? 'checked' : '';
    const titleAttr = escapeHtml(descValue).replace(/"/g, '&quot;');
    const escapedDesc = escapeHtml(descValue).replace(/\n/g, '<br>');
    html += `
      <tr>
        <td><input type="checkbox" class="tl-checkbox" data-id="${escapeHtml(c.id)}" ${checkedAttr}></td>
        <td class="cell-id">${escapeHtml(c.id)}</td>
        <td class="cell-title">${escapeHtml(c.title || '')}</td>
        <td class="cell-score">${c.score ? Number(c.score).toFixed(2) : ''}</td>
        <td class="cell-description" title="${titleAttr}">${escapedDesc}</td>
      </tr>`;
  });
  html += '</tbody></table>';
  cont.innerHTML = html;
}

function folderLeaf(folder) {
  if (!folder) return '';
  const parts = String(folder).replace(/\/+$/, '').split('/');
  return parts[parts.length - 1] || folder;
}

function renderZephyrTable(refs, existingSelections = []) {
  const cont = document.getElementById('zephyr-table');
  if (!refs || refs.length === 0) {
    cont.innerHTML = '<em>No relevant external Zephyr cross-refs found for this case.</em>';
    return;
  }
  const saved = {};
  existingSelections.forEach(s => { saved[s.id_or_key || s.key] = s.justification || ''; });

  let html = '<table class="table cols-6-zephyr"><thead><tr><th></th><th>Key</th><th>Title</th><th>Score</th><th>Area</th><th>Why / Description</th></tr></thead><tbody>';
  refs.forEach((r, idx) => {
    const hasSaved = Object.keys(saved).length > 0;
    const isChecked = saved.hasOwnProperty(r.key) || (!hasSaved && idx < 2);
    const why = (r.justification || saved[r.key] || '').trim();
    // Full case body (objective / steps) — do not prefer short saved justification over it
    let body = r.description || '';
    if (!body || body === r.title) {
      body = r.description || r.title || why || '';
    }
    const showWhy = why && body && body !== why && !body.includes(why.slice(0, Math.min(40, why.length)));
    const descValue = truncateText(body || why, DESC_SOFT_MAX);
    const checkedAttr = isChecked ? 'checked' : '';
    const score = (r.score !== undefined && r.score !== null) ? Number(r.score).toFixed(1) : '';
    const area = folderLeaf(r.folder);
    // Full "why" line (no 120-char cut); CSS scroll handles long cells
    const whyLine = showWhy
      ? `<div class="justification-note">${escapeHtml(truncateText(why, DESC_SOFT_MAX))}</div>`
      : '';
    const titleAttr = escapeHtml((whyLine ? why + '\n' : '') + descValue).replace(/"/g, '&quot;');
    const escapedDesc = escapeHtml(descValue).replace(/\n/g, '<br>');
    html += `
      <tr>
        <td><input type="checkbox" class="zephyr-checkbox" data-key="${escapeHtml(r.key)}" ${checkedAttr}></td>
        <td class="cell-id">${escapeHtml(r.key)}</td>
        <td class="cell-title">${escapeHtml(r.title || '')}</td>
        <td class="cell-score">${score}</td>
        <td class="cell-folder" title="${escapeHtml(r.folder || '')}">${escapeHtml(area)}</td>
        <td class="cell-description" title="${titleAttr}">${whyLine}${escapedDesc}</td>
      </tr>`;
  });
  html += '</tbody></table>';
  cont.innerHTML = html;
}

/** Short title = first line / text before [analysis]; body = rest or full description. */
function splitAtpTitleDescription(title, description, fallbackId) {
  const full = String(description || title || '').trim();
  let shortTitle = String(title || '').trim();
  // If title still contains the analysis blob, split it
  const br = shortTitle.indexOf('[');
  if (br > 0) {
    shortTitle = shortTitle.substring(0, br).trim();
  }
  if (!shortTitle || shortTitle === full) {
    const firstLine = full.split(/\n/)[0] || '';
    const m = full.match(/^([\s\S]*?)(?:\n\n?\[)/);
    shortTitle = (m ? m[1] : firstLine).trim().split('\n')[0].trim() || fallbackId || '';
  }
  // Prefer full source description for the body; do not re-concat title+desc
  let body = full;
  if (shortTitle && body.startsWith(shortTitle)) {
    body = body.slice(shortTitle.length).replace(/^\s*\n+/, '').trim() || full;
  }
  // If description was only a short reason and title held the long text, use title as body source
  if ((!description || description.length < 40) && title && title.length > (description || '').length) {
    const fromTitle = String(title).trim();
    const tbr = fromTitle.indexOf('[');
    if (tbr > 0) {
      shortTitle = fromTitle.substring(0, tbr).trim() || shortTitle;
      body = fromTitle.substring(tbr).trim();
    }
  }
  return { title: shortTitle || fallbackId || '', body: body || full || '' };
}

function renderATPTable(cands, existingSelections = []) {
  const cont = document.getElementById('atp-table');
  if (!cands || cands.length === 0) {
    cont.innerHTML = '<em>No ATPyLib candidates loaded for this case.</em>';
    return;
  }
  const saved = {};
  existingSelections.forEach(s => { saved[s.id_or_key] = s.justification || ''; });

  // Filter out non-functional tests for Step 3
  cands = cands.filter(c => {
    const t = ((c.title || '') + (c.description || '') + (c.id || '')).toLowerCase();
    return !t.includes('(not a functional test)');
  });

  let html = '<table class="table cols-6-atp"><thead><tr><th></th><th>ID</th><th>Title</th><th>Score</th><th>Src</th><th>Description</th></tr></thead><tbody>';
  cands.forEach((c, idx) => {
    const hasSaved = Object.keys(saved).length > 0;
    const isChecked = saved.hasOwnProperty(c.id) || (!hasSaved && idx < 3);
    // Prefer full source description; justification is LLM/search reason (not a substitute for body)
    const sourceDesc = c.description || '';
    const { title: titleText, body: descBody } = splitAtpTitleDescription(
      c.title || '',
      sourceDesc,
      c.id || ''
    );
    // Optional short note if justification differs and is not already in the body
    const just = (saved[c.id] || c.justification || c.reason || '').trim();
    let fullDesc = descBody;
    if (just && just.length > 8 && !fullDesc.includes(just.slice(0, Math.min(40, just.length)))) {
      // Keep justification out of Description when we already have full analysis text
      if (!fullDesc || fullDesc.length < 60) {
        fullDesc = just;
      }
    }
    // Soft safety only for pathological megabyte fields — real ATP texts are ~200–800 chars
    fullDesc = truncateText(fullDesc, DESC_SOFT_MAX);
    const checkedAttr = isChecked ? 'checked' : '';
    const score = (c.score !== undefined) ? Number(c.score).toFixed(2) : '';
    const suite = c.suite ? `<span class="cell-suite">(${escapeHtml(c.suite)})</span>` : '';
    const src = c.source || (c.justification && c.justification.indexOf('keyword') >= 0 ? 'keyword' : 'llm');
    const titleAttr = escapeHtml(fullDesc).replace(/"/g, '&quot;');
    const escapedDesc = escapeHtml(fullDesc).replace(/\n/g, '<br>');
    html += `
      <tr>
        <td><input type="checkbox" class="atp-checkbox" data-id="${escapeHtml(c.id)}" ${checkedAttr}></td>
        <td class="cell-id">${escapeHtml(c.id)}</td>
        <td class="cell-title">${escapeHtml(titleText)}${suite}</td>
        <td class="cell-score">${score}</td>
        <td class="cell-source">${escapeHtml(src)}</td>
        <td class="cell-description" title="${titleAttr}">${escapedDesc}</td>
      </tr>`;
  });
  html += '</tbody></table>';
  cont.innerHTML = html;
}

function truncateText(str, maxLen) {
  if (str == null) return '';
  const s = String(str);
  if (s.length <= maxLen) return s;
  return s.slice(0, Math.max(0, maxLen - 1)).trimEnd() + '…';
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, function(m) {
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m];
  });
}

/** data-args attribute value for the click dispatcher: JSON array, HTML-escaped. */
function dataArgs(...args) {
  return escapeHtml(JSON.stringify(args));
}

/** Resolve testScript from step5 (preferred) or legacy step4. */
function getSessionTestScript(sess) {
  const s = sess || currentSession || {};
  if (s.step5 && s.step5.testScript) return s.step5.testScript;
  if (s.step4 && s.step4.testScript) return s.step4.testScript;
  return { type: 'steps', steps: [] };
}

function getSessionObjective(sess) {
  const s = sess || currentSession || {};
  return ((s.step4 && s.step4.objective) || '').trim();
}

function renderObjectiveResult() {
  const container = document.getElementById('objective-result');
  if (!container) return;
  const obj = getSessionObjective();
  if (!obj) {
    container.innerHTML = '<em class="review-empty">No objective yet. Confirm steps 2–4, then click Synthesize Objectives.</em>';
    return;
  }
  const conf = !!(currentSession && currentSession.step4 && currentSession.step4.confirmed);
  const prov = (currentSession && currentSession.step4 && currentSession.step4.provenance) || null;
  let provenanceHtml = '';
  if (prov) {
    provenanceHtml = `
      <details class="provenance-details">
        <summary class="provenance-summary">LLM Provenance — objectives (click for details)</summary>
        <pre class="provenance-pre">${escapeHtml(JSON.stringify(prov, null, 2))}</pre>
      </details>`;
  }
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

function renderStepsResult() {
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
  const prov = (currentSession && currentSession.step5 && currentSession.step5.provenance)
    || (currentSession && currentSession.step4 && currentSession.step4.provenance)
    || null;
  let provenanceHtml = '';
  if (prov && (prov.steps_prompt || prov.phase === 'steps' || prov.phase === 'combined')) {
    provenanceHtml = `
      <details class="provenance-details">
        <summary class="provenance-summary">LLM Provenance — steps (click for details)</summary>
        <pre class="provenance-pre">${escapeHtml(JSON.stringify(prov, null, 2))}</pre>
      </details>`;
  }
  container.innerHTML = `
    <div class="section">
      <div class="section-heading">Test Steps (Human-Readable)</div>
      <div id="synth-steps-view">${stepsHtml}</div>
    </div>
    <div class="synth-actions" id="steps-edit-actions"></div>
    <div class="synth-actions" id="steps-export-actions">
      <button type="button" data-action="exportBundle" class="btn btn-export">Export Repeatable Bundle</button>
    </div>
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
  if (!currentSession) return;
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
  if (!currentSession || !currentKey) return;
  const objTa = document.getElementById('edit-objective');
  const objective = objTa ? objTa.value.trim() : getSessionObjective();
  if (!objective) {
    alert('Objective cannot be empty.');
    return;
  }
  try {
    const res = await fetch('/api/wizard/save_objective/' + encodeURIComponent(currentKey), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ objective, confirm: !!alsoConfirm }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    currentSession = data.session;
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
  if (!currentKey) return alert('Load a case first.');
  // Capture any in-progress textarea
  const objTa = document.getElementById('edit-objective');
  const body = {};
  if (objTa) body.objective = objTa.value.trim();
  try {
    const res = await fetch('/api/wizard/confirm_objectives/' + encodeURIComponent(currentKey), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    currentSession = data.session;
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
  if (!currentSession) return;
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
  if (!_editingSteps || !currentSession || !currentKey) return;
  document.querySelectorAll('#synth-steps-view .editable-step input').forEach(inp => {
    const idx = parseInt(inp.getAttribute('data-idx'), 10);
    const field = inp.getAttribute('data-field') || 'description';
    if (_editingSteps.steps[idx]) {
      _editingSteps.steps[idx][field] = inp.value.trim();
    }
  });
  try {
    const res = await fetch('/api/wizard/save_steps/' + encodeURIComponent(currentKey), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ testScript: { type: 'steps', steps: _editingSteps.steps } }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    currentSession = data.session;
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

function renderReviewSummary() {
  const cont = document.getElementById('review-summary-content');
  if (!cont) return;
  if (!currentSession) {
    cont.innerHTML = '<em class="review-empty">Load a case and confirm steps 2–4 to see selection previews.</em>';
    return;
  }

  const s1 = currentSession.step1 || {};
  const s2 = currentSession.step2 || {};
  const s3 = currentSession.step3 || {};

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

  const obj = getSessionObjective(currentSession);
  if (obj) {
    const conf = !!(currentSession.step4 && currentSession.step4.confirmed);
    const confBadge = conf
      ? ' <span class="badge badge-success">✓ Confirmed</span>'
      : ' <span class="badge">Draft</span>';
    const shortObj = obj.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    const preview = shortObj.length > 160 ? shortObj.slice(0, 157) + '…' : shortObj;
    html += `<div class="sel-group"><strong>Step 5 (Objective)</strong>${confBadge}: <span class="justification-note">${escapeHtml(preview)}</span></div>`;
  }

  cont.innerHTML = html;
}

async function setLLMConfig() {
  // Case is optional: without one the config is saved as the workspace default
  // (and copied onto cases as they load); with one it is also stored on that session.
  const key = currentKey || getActiveCaseKey();
  const model = document.getElementById('llmModel').value.trim();

  // Determine method from radio (the radios now directly select the subscription provider+mode)
  const methodRadios = document.querySelectorAll('input[name="llmAuthMethod"]');
  let auth_method = 'grok_cli';
  for (let r of methodRadios) {
    if (r.checked) { auth_method = r.value; break; }
  }

  let provider = (auth_method === 'claude_agent' || auth_method === 'claude_code') ? 'claude' : 'grok';

  const body = { provider, auth_method };
  // CLI subscription modes require no credential here
  if (model) body.model = model;

  const url = key
    ? `/api/wizard/set_llm_config/${encodeURIComponent(key)}`
    : '/api/wizard/set_llm_config';
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  });
  const data = await res.json();
  if (data.llm_config) {
    if (currentSession) currentSession.llm_config = data.llm_config;
    // Remember client-side too (survives until hard refresh; server also stores workspace default)
    window.lastLLMConfig = data.llm_config;
    try { localStorage.setItem('draftingLLMConfig', JSON.stringify({
      provider: data.llm_config.provider,
      auth_method: data.llm_config.auth_method,
      model: data.llm_config.model || null
    })); } catch (_) {}
    updateLLMStatus(data.llm_config);
    if (auth_method === 'claude_agent') {
      ckBrokerLoop();  // ensure the broker is running (idempotent) so jobs get served
      const a = await probeLocalAgent();
      if (a.ok && a.claude_cli) {
        alert("Claude (my local machine) enabled. Calls run through the ck-agent on YOUR machine against YOUR own Claude seat. Keep the agent running and this tab open.");
      } else if (a.ok && !a.claude_cli) {
        alert("Agent reachable, but the Claude CLI wasn't found on your machine. Install Claude Code and run 'claude' -> /login, then retry.");
      } else {
        alert("Claude (my local machine) selected, but your local agent isn't reachable.\n\nStart it: cd ask-ck/agent && ./run-agent.sh — then click 'Check my local agent'.");
      }
    } else if (auth_method === 'grok_cli') {
      const cli = data.llm_config.grok_cli || {};
      if (cli.available) {
        alert(`Grok CLI subscription mode enabled (CLI: ${cli.version || 'found'}). Calls use your local 'grok login' SuperGrok/X Premium+ session.`);
      } else {
        alert('Grok CLI mode set, but the CLI was NOT found.\n\n' + (cli.hint || 'Install grok CLI and run grok login --oauth, then re-apply.'));
      }
    }
    // No credential field anymore for subscription modes
  } else {
    alert('Failed to set LLM config: ' + (data.detail || data.message || 'unknown'));
  }
}

// --- Per-user local Claude agent (ck-agent on the USER's machine) -----------
const CK_AGENT_URL = (window.CK_AGENT_URL || 'http://127.0.0.1:8765');

async function probeLocalAgent() {
  // Ask the user's own ck-agent whether it's up and whether claude is installed.
  try {
    const res = await fetch(CK_AGENT_URL + '/health', { method: 'GET' });
    if (!res.ok) return { ok: false };
    const s = await res.json();
    return { ok: true, claude_cli: !!s.claude_cli, path: s.claude_path, hint: s.hint };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

// The broker loop: while claude_agent is the active LLM mode, continuously
// long-poll the shared server for prompt jobs for THIS session, run each on the
// user's own local agent, and post the completion back. This is the transport
// that lets the shared server use each user's own Claude seat.
let ckBrokerRunning = false;

function ckAgentModeActive() {
  const c = (currentSession && currentSession.llm_config) || window.lastLLMConfig || {};
  const am = (c.auth_method || '').toLowerCase();
  const radio = document.querySelector('input[name="llmAuthMethod"]:checked');
  return am === 'claude_agent' || (radio && radio.value === 'claude_agent');
}

async function ckBrokerLoop() {
  if (ckBrokerRunning) return;      // single loop per tab
  ckBrokerRunning = true;
  while (true) {
    try {
      // Long-poll for the next job (server holds up to ~25s). Header added by patchFetch.
      const res = await fetch(`/api/agent/next?session=${encodeURIComponent(CK_SESSION_ID)}&wait=25`);
      if (!res.ok) { await new Promise(r => setTimeout(r, 2000)); continue; }
      const data = await res.json();
      const job = data.job;
      if (!job) continue;           // timed out with no work — poll again
      // Run it on the user's own local agent.
      let content = '', error = false;
      try {
        const ares = await fetch(CK_AGENT_URL + '/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: job.prompt, model: job.model, timeout: 600 }),
        });
        const ajson = await ares.json();
        content = ajson.content || '';
        error = !!ajson.error;
      } catch (e) {
        content = 'ERROR: local agent unreachable — is ck-agent running? ' + e;
        error = true;
      }
      // Deliver the completion back to the shared server.
      await fetch('/api/agent/result', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: job.job_id, content, error }),
      });
    } catch (e) {
      await new Promise(r => setTimeout(r, 2000));   // transient error — back off, keep going
    }
  }
}

async function checkLocalAgent() {
  const resultDiv = document.getElementById('agentStatusResult');
  if (resultDiv) resultDiv.innerHTML = '<em class="status-muted">Checking your local agent…</em>';
  const s = await probeLocalAgent();
  if (!resultDiv) return;
  if (!s.ok) {
    resultDiv.innerHTML = `<span class="status-err">&#10007; Agent not reachable at ${escapeHtml(CK_AGENT_URL)}.</span> `
      + `Start it: <code>cd ask-ck/agent &amp;&amp; ./run-agent.sh</code>, then retry.`;
  } else if (!s.claude_cli) {
    resultDiv.innerHTML = `<span class="status-err">&#10007; Agent up, but Claude CLI not found on your machine.</span> ${escapeHtml(s.hint || "Install Claude Code and run 'claude' -> /login.")}`;
  } else {
    resultDiv.innerHTML = `<span class="status-ok">&#10003; Local agent ready</span> <span class="status-muted">(claude at ${escapeHtml(s.path || '')})</span><br><span class="status-muted">Prompts will run on YOUR machine against YOUR own seat while this tab is open.</span>`;
  }
}

async function checkGrokCLIStatus() {
  const resultDiv = document.getElementById('grokCliStatusResult');
  if (resultDiv) resultDiv.innerHTML = '<em class="status-muted">Checking Grok CLI…</em>';
  try {
    const res = await fetch('/api/wizard/grok_cli_status');
    const s = await res.json();
    if (resultDiv) {
      if (s.available) {
        resultDiv.innerHTML = `<span class="status-ok">&#10003; Grok CLI found</span> — ${escapeHtml(s.version || '')} <span class="status-muted">(${escapeHtml(s.path || '')})</span><br><span class="status-muted">Note: login state verified on first call. Make sure you ran 'grok login' with your subscription.</span>`;
      } else {
        resultDiv.innerHTML = `<span class="status-err">&#10007; Not found.</span> ${escapeHtml(s.hint || '')}`;
      }
    }
  } catch (e) {
    if (resultDiv) resultDiv.innerHTML = `<span class="status-err">Status check failed: ${escapeHtml(String(e))}</span>`;
  }
}

function normalizeLLMConfig(config) {
  // Normalize server/session llm_config for status display.
  const c = Object.assign({}, config || {});
  const am = (c.auth_method || '').toLowerCase();
  // Session dict does not include has_key; treat CLI modes as configured
  if (c.has_key === undefined) {
    c.has_key = !!(c.api_key || c.token) || am === 'claude_agent' || am === 'claude_code' || am === 'grok_cli';
  }
  return c;
}

function updateLLMStatus(config) {
  const statusEl = document.getElementById('llmStatus');
  const sidebarEl = document.getElementById('llm-status-sidebar');

  let c = config || (currentSession && currentSession.llm_config) || window.lastLLMConfig || {};
  c = normalizeLLMConfig(c);
  const provider = c.provider || '';
  const am = (c.auth_method || '').toLowerCase();
  const cliMode = (am === 'claude_agent' || am === 'claude_code' || am === 'grok_cli');
  const hasCred = !!(c.has_key || c.api_key || c.token || cliMode);

  let text = '';
  let ok = false;

  if (!provider || !hasCred) {
    text = 'No credential (use CLI login or set key)';
    ok = false;
  } else {
    const p = provider === 'grok' ? 'Grok (xAI)' : (provider === 'claude' ? 'Claude' : provider);
    let m = ' (API key)';
    if (am === 'claude_agent') m = ' (Claude — my local machine)';
    else if (am === 'claude_code') m = ' (Claude Code CLI)';
    else if (am === 'grok_cli') m = ' (Grok CLI subscription)';
    text = `Using ${p}${m}`;
    ok = true;
  }

  [statusEl, sidebarEl].forEach(el => {
    if (!el) return;
    el.textContent = text;
    el.classList.remove('llm-status-ok', 'llm-status-warn');
    el.classList.add(ok ? 'llm-status-ok' : 'llm-status-warn');
  });
}

function updateLLMDefaults() {
  // Adjust model placeholder from the selected subscription radio only.
  // IMPORTANT: do not call updateAuthMethodUI() here — that used to recurse forever
  // (updateAuthMethodUI → updateLLMDefaults → updateAuthMethodUI → …) and crash Load
  // with "RangeError: Maximum call stack size exceeded".
  const modelInput = document.getElementById('llmModel');
  if (!modelInput || modelInput.value) return;

  const checked = document.querySelector('input[name="llmAuthMethod"]:checked');
  if (checked && checked.value === 'claude_agent') {
    modelInput.placeholder = '(Claude CLI default)';
  } else {
    modelInput.placeholder = '(Grok CLI default)';
  }
}

function updateAuthMethodUI() {
  // Radios now directly choose the subscription CLI mode (no dropdown, no API key)
  const method = document.querySelector('input[name="llmAuthMethod"]:checked')?.value || 'grok_cli';
  const agentBtn = document.getElementById('agentStatusBtn');
  const grokBtn = document.getElementById('grokCliStatusBtn');
  const agentInstr = document.getElementById('claudeAgentInstructions');
  const grokInstr = document.getElementById('grokCliInstructions');

  if (method === 'claude_agent') {
    if (agentBtn) agentBtn.classList.remove('hidden');
    if (agentInstr) agentInstr.classList.remove('hidden');
    if (grokBtn) grokBtn.classList.add('hidden');
    if (grokInstr) grokInstr.classList.add('hidden');
  } else {
    // grok_cli
    if (grokBtn) grokBtn.classList.remove('hidden');
    if (grokInstr) grokInstr.classList.remove('hidden');
    if (agentBtn) agentBtn.classList.add('hidden');
    if (agentInstr) agentInstr.classList.add('hidden');
  }

  // Placeholder only (no reverse call into this function)
  updateLLMDefaults();
}

function restoreLLMUI() {
  // Prefer active session config; fall back to last applied / localStorage
  let c = currentSession && currentSession.llm_config;
  const am = c && (c.auth_method || '').toLowerCase();
  const sessionActive = c && (am === 'claude_agent' || am === 'claude_code' || am === 'grok_cli' || c.api_key || c.token || c.has_key);
  if (!sessionActive) {
    c = window.lastLLMConfig || null;
    if (!c) {
      try {
        const raw = localStorage.getItem('draftingLLMConfig');
        if (raw) c = JSON.parse(raw);
      } catch (_) {}
    }
  }
  if (!c || !c.provider) return;

  // Set method from saved config (no provider dropdown; radios embody the choice)
  let method = c.auth_method || 'grok_cli';
  if (method === 'account' || method === 'api_key') method = 'grok_cli';  // legacy mappings
  if (method === 'claude_code') method = 'claude_agent';  // server-local CLI removed from UI; map to per-user agent
  const radios = document.querySelectorAll('input[name="llmAuthMethod"]');
  for (let r of radios) {
    r.checked = (r.value === method);
  }

  // Keep model field in sync when present
  const modelInput = document.getElementById('llmModel');
  if (modelInput && c.model && !modelInput.value) {
    modelInput.value = c.model;
  }

  updateAuthMethodUI();
  updateLLMStatus(normalizeLLMConfig(c));
  if (method === 'claude_agent') ckBrokerLoop();  // resume serving jobs for a returning agent user
}

async function confirmStep(step) {
  if (!currentKey) return alert('Load a case first');

  let body = {};
  if (step === 1) {
    const sels = [];
    document.querySelectorAll('#tl-table .tl-checkbox:checked').forEach(cb => {
      const id = cb.dataset.id;
      const cand = (window.currentTestLink || []).find(x => x.id === id) || {};
      sels.push({
        id_or_key: id,
        title: cand.title || id,
        justification: cand.description || cand.snippet || cand.title || ''
      });
    });
    body = { selections: sels };
  } else if (step === 2) {
    const sels = [];
    document.querySelectorAll('#zephyr-table .zephyr-checkbox:checked').forEach(cb => {
      const k = cb.dataset.key;
      const ref = (window.currentZephyr || []).find(x => x.key === k) || {};
      sels.push({
        id_or_key: k,
        title: ref.title || k,
        justification: ref.description || ref.title || ''
      });
    });
    body = { selections: sels };
  } else if (step === 3) {
    const sels = [];
    document.querySelectorAll('#atp-table input.atp-checkbox:checked').forEach(cb => {
      const id = cb.dataset.id;
      const atp = (window.currentATP || []).find(x => x.id === id) || {};
      const title = atp.title || ('ATPyLib ' + id);
      sels.push({ 
        id_or_key: id, 
        title: title, 
        justification: atp.description || atp.justification || atp.reason || '' 
      });
    });
    body = { selections: sels };
  }

  const res = await fetch(`/api/wizard/confirm_step/${currentKey}/${step}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  });
  const data = await res.json();
  currentSession = data.session;
  updateUI();
  if (data.can_synthesize) alert('All reviews confirmed. Go to Step 5 (Objective Synthesis).');
}

async function synthesizeObjectives() {
  if (!currentSession) return alert('Load a case and confirm steps 2–4 first.');
  const btnNote = 'Synthesizing objectives (LLM)…';
  try {
    const res = await fetch('/api/wizard/synthesize_objectives', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session: currentSession, use_llm: true }),
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(t.slice(0, 300) || ('status ' + res.status));
    }
    const data = await res.json();
    currentSession = data.session;
    renderObjectiveResult();
    updateUI();
    goToStep(4);
  } catch (e) {
    alert('Objective synthesis failed: ' + e);
  }
}

async function synthesizeSteps() {
  if (!currentSession) return alert('Load a case first.');
  if (!getSessionObjective()) {
    alert('No objective yet. Complete Step 5 (Objective Synthesis) and confirm first.');
    goToStep(4);
    return;
  }
  try {
    const res = await fetch('/api/wizard/synthesize_steps', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session: currentSession, use_llm: true }),
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(t.slice(0, 300) || ('status ' + res.status));
    }
    const data = await res.json();
    currentSession = data.session;
    const synth = data.synthesized || {};
    if (synth.validation && synth.validation.valid === false) {
      console.warn('Steps validation issues:', synth.validation.issues);
    }
    renderStepsResult();
    updateUI();
    goToStep(5);
  } catch (e) {
    alert('Test step synthesis failed: ' + e);
  }
}

/** @deprecated Use synthesizeObjectives / synthesizeSteps */
async function synthesize() {
  return synthesizeObjectives();
}

async function exportBundle() {
  if (!currentSession) return;
  try {
    const res = await fetch('/api/wizard/export', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({session: currentSession})
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(t.slice(0, 300) || ('status ' + res.status));
    }
    const data = await res.json();
    const v = data.validation || {};
    if (v.valid === false) {
      console.warn('Export validation issues:', v.issues);
    }

    // Primary behaviour: server writes drop-in artefacts under refined-cases/.
    // No browser Downloads prompts (those were leftover convenience, not the intended path).
    const savedTo = data.saved_to || ('refined-cases/<Group>/' + (currentKey || 'case'));
    const files = (data.saved_files && data.saved_files.length)
      ? data.saved_files.join(', ')
      : 'traceability.md, zephyr_payload.json, ' + (currentKey || 'case') + '-session.json';
    let msg = 'Export complete — saved on the server (not browser Downloads).\n\n'
      + 'Path:\n  ' + savedTo + '/\n\n'
      + 'Files:\n  ' + files + '\n\n'
      + 'These are drop-in for the refined-cases layout and upload tooling.';
    if (data.message && !data.saved_to) {
      msg = data.message;
    }
    if (v.valid === false) {
      msg += '\n\nValidation reported issues (see browser console).';
    }
    alert(msg);

    // Case may have moved into Complete — refresh dual dropdowns
    try { await refreshCaseSelects(currentKey); } catch (_) {}
  } catch (e) {
    alert('Export failed: ' + e);
  }
}

async function clearCurrentSession() {
  if (!currentKey) currentKey = getActiveCaseKey();
  if (!currentKey) return alert('No case selected');

  if (!confirm(`Clear case session for ${currentKey}?\nSelections / confirms / synthesis for this case will be reset.\nYour workspace LLM preference (CLI login) is kept.`)) {
    return;
  }

  try {
    const res = await fetch(`/api/wizard/clear_session/${currentKey}`, { method: 'POST' });
    if (res.ok) {
      alert('Case session cleared. Workspace LLM preference is kept.');
      // Reset case state only (LLM preference is workspace-scoped)
      currentSession = null;

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

function fillCaseSelect(sel, grouped, placeholder) {
  if (!sel) return;
  while (sel.options.length > 0) sel.remove(0);
  const ph = document.createElement('option');
  ph.value = '';
  ph.text = placeholder || 'Select case…';
  sel.appendChild(ph);
  (grouped || []).forEach(grp => {
    const cases = grp.cases || [];
    if (!cases.length) return;
    const og = document.createElement('optgroup');
    og.label = grp.label || 'Cases';
    cases.forEach(c => {
      const o = document.createElement('option');
      const key = c.key || c;
      const title = c.title || '';
      o.value = key;
      o.text = title ? `${key} — ${title}` : key;
      og.appendChild(o);
    });
    sel.appendChild(og);
  });
}

function syncHiddenCaseSel(key) {
  const hidden = document.getElementById('caseSel');
  if (!hidden) return;
  while (hidden.options.length > 0) hidden.remove(0);
  const o = document.createElement('option');
  o.value = key || '';
  o.text = key || '';
  o.selected = true;
  hidden.appendChild(o);
}

function handleCasePairChange(openSel, doneSel, sourceSel, onSelect) {
  const key = sourceSel.value || null;

  // Mutual exclusivity: selecting in one clears the other
  if (sourceSel === openSel && doneSel) doneSel.value = '';
  if (sourceSel === doneSel && openSel) openSel.value = '';

  const selectedOpt = sourceSel.options[sourceSel.selectedIndex];
  let title = null;
  if (selectedOpt && selectedOpt.text.includes(' — ')) {
    title = selectedOpt.text.split(' — ').slice(1).join(' — ');
  }
  onSelect(key, title);
}

function onCaseSelectChange(sourceSel) {
  const openSel = document.getElementById('caseSelOpen');
  const doneSel = document.getElementById('caseSelDone');
  handleCasePairChange(openSel, doneSel, sourceSel, (key, title) => {
    currentKey = key;
    window.currentCaseTitle = title;
    syncHiddenCaseSel(key);
    updatePageHeader();
  });
}

function onPtCaseSelectChange(sourceSel) {
  // PyTest Creator: single Complete-cases dropdown. Must never touch currentKey /
  // #caseSel / the page header — those belong to the Generator's loaded case.
  handleCasePairChange(null, null, sourceSel, (key, title) => {
    ptCase = { key: key, title: title };
    const s = document.getElementById('pt-selected-summary');
    if (s) s.textContent = key ? `Selected: ${key}` : '';
  });
}

function getActiveCaseKey() {
  const openSel = document.getElementById('caseSelOpen');
  const doneSel = document.getElementById('caseSelDone');
  const hidden = document.getElementById('caseSel');
  if (openSel && openSel.value) return openSel.value;
  if (doneSel && doneSel.value) return doneSel.value;
  if (hidden && hidden.value) return hidden.value;
  return currentKey || null;
}

let _caseSelectListenersBound = false;

// Dynamic case lists: open/partial vs complete (from refined-cases + sessions)
async function refreshCaseSelects(preserveKey) {
  const openSel = document.getElementById('caseSelOpen');
  const doneSel = document.getElementById('caseSelDone');
  const keep = preserveKey || getActiveCaseKey();

  try {
    const res = await fetch('/api/wizard/cases');
    if (res.ok) {
      const d = await res.json();
      const counts = d.counts || {};
      const openLabel = document.getElementById('caseSelOpenLabel');
      const doneLabel = document.getElementById('caseSelDoneLabel');
      if (openLabel) {
        const n = counts.incomplete != null ? counts.incomplete : '—';
        const ip = counts.in_progress != null ? counts.in_progress : '?';
        openLabel.innerHTML = `Open / partial <span class="case-count">(${n}; ${ip} in progress)</span>`;
      }
      if (doneLabel) {
        doneLabel.innerHTML = `Complete <span class="case-count">(${counts.complete != null ? counts.complete : '—'})</span>`;
      }

      const openGrouped = (d.incomplete && d.incomplete.grouped) || d.grouped || [];
      const doneGrouped = (d.complete && d.complete.grouped) || [];
      fillCaseSelect(openSel, openGrouped, 'Select open or partial case…');
      fillCaseSelect(doneSel, doneGrouped, 'Select completed case…');

      // PyTest Creator: Complete cases only (independent selection state)
      const ptDoneSel = document.getElementById('ptCaseSelDone');
      fillCaseSelect(ptDoneSel, doneGrouped, 'Select completed case…');
      const ptDoneLabel = document.getElementById('ptCaseSelDoneLabel');
      if (ptDoneLabel && doneLabel) ptDoneLabel.innerHTML = doneLabel.innerHTML;
      if (ptCase.key) {
        if (ptDoneSel && Array.from(ptDoneSel.options).some(o => o.value === ptCase.key)) {
          ptDoneSel.value = ptCase.key;
        } else {
          ptCase = { key: null, title: null };
          const s = document.getElementById('pt-selected-summary');
          if (s) s.textContent = '';
        }
      }

      // Restore selection into the correct dropdown
      if (keep) {
        const inOpen = openSel && Array.from(openSel.options).some(o => o.value === keep);
        const inDone = doneSel && Array.from(doneSel.options).some(o => o.value === keep);
        if (inDone && doneSel) {
          doneSel.value = keep;
          if (openSel) openSel.value = '';
          onCaseSelectChange(doneSel);
        } else if (inOpen && openSel) {
          openSel.value = keep;
          if (doneSel) doneSel.value = '';
          onCaseSelectChange(openSel);
        }
      }
    }
  } catch (e) {
    if (openSel && openSel.options.length === 0) {
      const o = document.createElement('option');
      o.value = '';
      o.text = 'Select case (offline)';
      openSel.appendChild(o);
    }
  }
}

async function initCases() {
  const openSel = document.getElementById('caseSelOpen');
  const doneSel = document.getElementById('caseSelDone');
  const ptDoneSel = document.getElementById('ptCaseSelDone');
  if (!_caseSelectListenersBound) {
    if (openSel) openSel.addEventListener('change', () => onCaseSelectChange(openSel));
    if (doneSel) doneSel.addEventListener('change', () => onCaseSelectChange(doneSel));
    if (ptDoneSel) ptDoneSel.addEventListener('change', () => onPtCaseSelectChange(ptDoneSel));
    _caseSelectListenersBound = true;
  }
  await refreshCaseSelects();
}

// ============================================================================
// Collapsible sidebar sections (accordion — one open at a time, all collapsed
// by default). Built at load time from the existing label+content markup so no
// section HTML had to be restructured. Each .sidebar-section-label owns the
// sibling nodes up to the next label as its "body".
// ============================================================================
function initSidebarAccordion() {
  const labels = Array.from(document.querySelectorAll('.sidebar .sidebar-section-label'));
  labels.forEach((label, i) => {
    // Collect this section's body nodes (until the next label).
    const body = [];
    let n = label.nextElementSibling;
    while (n && !n.classList.contains('sidebar-section-label')) {
      body.push(n);
      n = n.nextElementSibling;
    }
    label.classList.add('collapsible');
    label.dataset.sectionIndex = String(i);
    body.forEach(el => { el.classList.add('sidebar-section-body'); el.dataset.sectionIndex = String(i); });
    // caret indicator
    if (!label.querySelector('.section-caret')) {
      const caret = document.createElement('span');
      caret.className = 'section-caret';
      caret.textContent = '▸';
      label.appendChild(caret);
    }
    label.addEventListener('click', () => toggleSidebarSection(i));
  });
  collapseAllSections();
}

function collapseAllSections() {
  document.querySelectorAll('.sidebar .sidebar-section-label.collapsible')
    .forEach(l => l.classList.remove('section-open'));
  document.querySelectorAll('.sidebar .sidebar-section-body')
    .forEach(b => b.classList.add('section-collapsed'));
}

function openSidebarSection(i) {
  collapseAllSections();  // accordion: only one open
  const label = document.querySelector(`.sidebar-section-label.collapsible[data-section-index="${i}"]`);
  if (label) label.classList.add('section-open');
  document.querySelectorAll(`.sidebar-section-body[data-section-index="${i}"]`)
    .forEach(b => b.classList.remove('section-collapsed'));
}

function toggleSidebarSection(i) {
  const label = document.querySelector(`.sidebar-section-label.collapsible[data-section-index="${i}"]`);
  if (label && label.classList.contains('section-open')) collapseAllSections();
  else openSidebarSection(i);
}

function expandSectionForActivePanel(panelId) {
  // Find the sidebar item for this panel and open its owning section.
  const item = document.querySelector(`.sidebar-nav-item[data-panel="${panelId}"]`)
    || (/^step-\d+$/.test(panelId)
        ? document.querySelector(`.sidebar-nav-item[data-step="${panelId.slice(5)}"]`)
        : null);
  if (!item) return;
  const body = item.closest('.sidebar-section-body');
  if (body && body.dataset.sectionIndex != null) openSidebarSection(body.dataset.sectionIndex);
}

initSidebarAccordion();
initCases();
updateAuthMethodUI();
currentStep = 0;              // Generator defaults to step 0 when first opened
goToPanel('panel-main');     // Landing view = Main splash / Help home
updateLLMStatus();
loadToolStatus('zephyr-tool', 'zt-info-status');
loadToolStatus('test-composer', 'tc-status');

// Prefer first open/partial case if none chosen (no demo auto-load of a specific key)
setTimeout(() => {
  const openSel = document.getElementById('caseSelOpen');
  if (openSel && !openSel.value) {
    for (let i = 0; i < openSel.options.length; i++) {
      const v = openSel.options[i].value;
      if (v && v !== '') {
        openSel.selectedIndex = i;
        onCaseSelectChange(openSel);
        break;
      }
    }
  }
  updatePageHeader();
}, 200);

function goToPanel(panelId) {
  currentPanel = panelId;
  // Exactly one .tool-panel card visible at a time
  document.querySelectorAll('.tool-panel').forEach((el) => {
    el.classList.toggle('hidden', el.id !== panelId);
  });
  // Exactly one sidebar item active across ALL tool sections. Generator items
  // are addressed via their numeric data-step ('step-N'); other tools via data-panel.
  document.querySelectorAll('.sidebar-nav-item').forEach((item) => {
    const target = item.dataset.panel || (item.dataset.step !== undefined ? 'step-' + item.dataset.step : null);
    item.classList.toggle('active', target === panelId);
  });

  // Keep the active panel's sidebar section expanded (accordion).
  if (typeof expandSectionForActivePanel === 'function') expandSectionForActivePanel(panelId);

  updatePageHeader();

  // Session debug JSON is the Generator's currentSession — only meaningful on the
  // Objective/Test Case Generator step panels (step-0..step-5), not other tools/Main.
  const dbg = document.getElementById('session-debug');
  if (dbg) dbg.classList.toggle('hidden', !/^step-\d+$/.test(panelId));

  const ptRenderers = {
    'panel-pt-seq': renderPtSeqPanel,
    'panel-pt-search': renderPtSearchPanel,
    'panel-pt-fit': renderPtFitPanel,
    'panel-pt-frag': renderPtFragPanel,
    'panel-pt-gen': renderPtGenPanel,
    'panel-pt-run': renderPtRunPanel,
    'panel-pt-validate': renderPtValidatePanel,
    'panel-pt-testbox': renderPtTestboxPanel,
  };
  if (ptRenderers[panelId]) ptRenderers[panelId]();
}

function goToStep(step) {
  // Generator navigation. The numeric step scheme (data-step / step-N ids /
  // session keys step1..step5 / confirm_step 1-3) is load-bearing — sidebar
  // labels renumbered 1-6 are display-only and do NOT shift these values.
  currentStep = step;
  goToPanel('step-' + step);

  if (step === 4) {
    renderReviewSummary();
    renderObjectiveResult();
  }
  if (step === 5) {
    renderStepsResult();
  }
}

function updatePageHeader() {
  const titleEl = document.querySelector('.page-title');
  const descEl = document.querySelector('.page-description');
  if (!titleEl || !descEl) return;

  // The Main splash carries its own hero header; hide the page header there.
  const headerEl = document.querySelector('.page-header');
  if (headerEl) headerEl.classList.toggle('hidden', currentPanel === 'panel-main');

  // Keyed by panel id. Generator panels (step-N) show the loaded case as the
  // title; tool panels carry a static title override.
  const PANEL_META = {
    'step-0': { desc: 'Select a test case to work on.' },
    'step-1': { desc: 'Review TestLink candidates; search or suggest, then confirm.' },
    'step-2': { desc: 'Review external Zephyr cross-refs; search or suggest, then confirm.' },
    'step-3': { desc: 'Review scored ATPyLib candidates and confirm selections.' },
    'step-4': { desc: 'Synthesize and confirm objective artefacts from the review summary.' },
    'step-5': { desc: 'Synthesize test steps from the finalized objective, then export.' },
    'panel-main': { title: 'Ask CK', desc: 'Home — welcome and step-by-step guides for each tool.' },
    'panel-llm-config': { title: 'LLM Provider Login', desc: 'Log in to an LLM provider via a local subscription CLI.' },
    'panel-zt-info': { title: 'Zephyr Templating Tool', desc: 'Step 1: Info — under construction.' },
    'panel-zt-plan': { title: 'Zephyr Templating Tool', desc: 'Step 2: Test Plan / Cycle / Cases — under construction.' },
    'panel-zt-link': { title: 'Zephyr Templating Tool', desc: 'Step 3: Link Test Scripts — under construction.' },
    'panel-zt-tbd': { title: 'Zephyr Templating Tool', desc: 'Step 4: TBD — under construction.' },
    'panel-tc-tbd': { title: 'Test Composer', desc: 'Step 1: TBD — under construction.' },
    'panel-pt-cases': { title: 'PyTest Creator', desc: 'Select a completed case to turn into a framework test script.' },
    'panel-pt-seq': { title: 'PyTest Creator', desc: 'Step 2: identify the prescriptive test-step sequence, then confirm.' },
    'panel-pt-search': { title: 'PyTest Creator', desc: 'Step 3: search the script databases for full/partial coverage, then confirm.' },
    'panel-pt-fit': { title: 'PyTest Creator', desc: 'Step 4: decide reuse / extend / new, then confirm.' },
    'panel-pt-frag': { title: 'PyTest Creator', desc: 'Step 5: gather reusable code fragments, then confirm.' },
    'panel-pt-gen': { title: 'PyTest Creator', desc: 'Step 6: generate, name, lint and save the composite script, then confirm.' },
    'panel-pt-run': { title: 'PyTest Creator', desc: 'Step 7: execute on a stored testbox and review the parsed log.' },
    'panel-pt-validate': { title: 'PyTest Creator', desc: 'Step 8: final validation loop — fix with LLM until all cases PASS.' },
    'panel-pt-testbox': { title: 'PyTest Creator', desc: 'Manage stored testbox connections for the Run step.' }
  };

  const eyebrowEl = document.querySelector('.page-eyebrow');
  const meta = PANEL_META[currentPanel] || {};
  if (meta.title) {
    if (eyebrowEl) eyebrowEl.textContent = '';
    titleEl.textContent = meta.title;
    descEl.textContent = meta.desc || '';
    return;
  }
  // Generator panels (step-N): static tool eyebrow above the dynamic case title.
  if (eyebrowEl) eyebrowEl.textContent = 'Objective / Test Case Generator';
  if (currentKey) {
    const t = window.currentCaseTitle || '';
    titleEl.textContent = t ? `${currentKey} — ${t}` : currentKey;
  } else {
    titleEl.textContent = 'No case loaded';
  }
  descEl.textContent = meta.desc || 'Review data sources then synthesize with LLM.';
}

// ============================================================================
// PyTest Creator (see ask-ck/pytest-create/PLAN-pytest-creator.md)
// Session state lives server-side (sessions/pt-{key}.json); this module renders
// it and drives the gated flow. ptSession mirrors the server PtSession.
// ============================================================================
let ptSession = null;          // server session for ptCase.key
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
  if (!ptCase.key || !ptSession) {
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
  const before = ptCase.key;
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
  if (!ptCase.key) { alert('Select a completed case first.'); return; }
  const st = ptStatusEl('pt-load-status');
  const d = await ptApi(`/load_case/${ptCase.key}`, { method: 'POST' }, st);
  if (!d) return;
  ptSession = d.session;
  ptCaseInfo = { title: d.case_title, group_display: d.group_display,
                 objective: d.objective, steps: d.steps };
  updatePtBadges();
  goToPanel('panel-pt-seq');
}

async function ptRefreshSession() {
  if (!ptCase.key) return;
  const d = await ptApi(`/session/${ptCase.key}`);
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
  const d = await ptApi(`/confirm_step/${ptCase.key}/${step}`, { method: 'POST', body: '{}' });
  if (d) { ptSession = d.session; updatePtBadges(); }
}

// --- Step 2: Sequence -------------------------------------------------------

function renderPtSeqPanel() {
  const caseEl = document.getElementById('pt-seq-case');
  if (!ptCase.key || !ptSession) {
    caseEl.innerHTML = '<em class="review-empty">No case loaded — go to </em>'
      + '<a href="#" data-action="goToPanel" data-args="[&quot;panel-pt-cases&quot;]">1. Cases</a>.';
    document.getElementById('pt-seq-list').innerHTML = '';
    return;
  }
  caseEl.innerHTML = `<b>Case:</b> <span class="sel-label">${escapeHtml(ptCase.key)}</span>`
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
  const d = await ptApi(`/extract_sequence/${ptCase.key}`, { method: 'POST' }, ptStatusEl('pt-seq-status'));
  btn.disabled = false;
  if (!d) return;
  await ptRefreshSession();
  ptRenderSequence(d.sequence || []);
  if (d.notes) ptStatusEl('pt-seq-status').textContent = 'LLM notes: ' + d.notes;
}

async function ptSaveSequence() {
  if (!ptRequireCase()) return;
  const seq = ptCollectSequence();
  if (!seq.length) { alert('Sequence is empty.'); return; }
  const d = await ptApi(`/save_sequence/${ptCase.key}`, {
    method: 'POST', body: JSON.stringify({ sequence: seq }),
  }, ptStatusEl('pt-seq-status'));
  if (d) { await ptRefreshSession(); ptStatusEl('pt-seq-status').textContent = 'Saved.'; }
}

// --- Step 3: Script Search --------------------------------------------------

function renderPtSearchPanel() {
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

async function ptManualSearch() {
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
  const d = await ptApi(`/suggest_scripts/${ptCase.key}`, {
    method: 'POST',
    body: JSON.stringify({ user_inputs: document.getElementById('pt-user-inputs').value }),
  }, ptStatusEl('pt-search-status'));
  btn.disabled = false;
  if (!d) return;
  await ptRefreshSession();
  ptRenderMatches(d.matches || [], ((ptSession || {}).step3 || {}).selections || []);
  ptStatusEl('pt-search-status').textContent =
    `${(d.matches || []).length} candidates (from ${d.mechanical_considered} mechanically scored). Tick the ones to carry into steps 4-5.`;
}

async function ptSaveMatches() {
  if (!ptRequireCase()) return;
  const sels = Array.from(document.querySelectorAll('.pt-match-sel:checked')).map(c => c.value);
  const d = await ptApi(`/save_matches/${ptCase.key}`, {
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

function renderPtFitPanel() {
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

function ptFitEdited() { /* decision select edited; persisted on Save */ }

async function ptAssessFit() {
  if (!ptRequireCase()) return;
  const btn = document.getElementById('pt-fit-btn');
  btn.disabled = true;
  const d = await ptApi(`/assess_fit/${ptCase.key}`, { method: 'POST' }, ptStatusEl('pt-fit-status'));
  btn.disabled = false;
  if (!d) return;
  await ptRefreshSession();
  renderPtFitPanel();
}

async function ptSaveFit() {
  if (!ptRequireCase()) return;
  const dec = document.getElementById('pt-fit-decision').value;
  if (!dec) { alert('Pick a decision first.'); return; }
  const s4 = ptSession.step4 || {};
  const d = await ptApi(`/save_fit/${ptCase.key}`, {
    method: 'POST',
    body: JSON.stringify({ decision: dec, base_script: s4.base_script || null }),
  }, ptStatusEl('pt-fit-status'));
  if (d) { await ptRefreshSession(); renderPtFitPanel(); ptStatusEl('pt-fit-status').textContent = 'Saved.'; }
}

// --- Step 5: Fragments --------------------------------------------------------

function renderPtFragPanel() {
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
  const d = await ptApi(`/gather_fragments/${ptCase.key}`, { method: 'POST' }, ptStatusEl('pt-frag-status'));
  btn.disabled = false;
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
  const d = await ptApi(`/save_fragments/${ptCase.key}`, {
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

function renderPtGenPanel() {
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
  const d = await ptApi(`/generate_script/${ptCase.key}`, {
    method: 'POST',
    body: JSON.stringify({
      group: document.getElementById('pt-gen-group').value.trim(),
      name: document.getElementById('pt-gen-name').value.trim(),
    }),
  }, ptStatusEl('pt-gen-status'));
  btn.disabled = false;
  if (!d) return;
  await ptRefreshSession();
  renderPtGenPanel();
}

async function ptLintScript() {
  if (!ptRequireCase()) return;
  // push current edits into the session first so lint sees them
  await ptPushCodeEdits(false);
  const d = await ptApi(`/lint_script/${ptCase.key}`, { method: 'POST' }, ptStatusEl('pt-gen-status'));
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
  return await ptApi(`/save_script/${ptCase.key}`, {
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

async function renderPtRunPanel() {
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

function ptProfileSelected(sel) {
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
  const d = await ptApi(`/run/${ptCase.key}`, {
    method: 'POST',
    body: JSON.stringify({ profile, setup: setupPath || setupName }),
  }, ptStatusEl('pt-run-status'));
  if (!d) return;
  ptStatusEl('pt-run-status').textContent = `Run ${d.run_id} queued…`;
  if (ptRunPoll) clearInterval(ptRunPoll);
  ptRunPoll = setInterval(() => ptPollRun(d.run_id), 4000);
}

async function ptPollRun(runId) {
  const d = await ptApi(`/run_status/${ptCase.key}/${runId}?tail=60`);
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

function renderPtValidatePanel() {
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
  const d = await ptApi(`/validate/${ptCase.key}`, { method: 'POST' }, ptStatusEl('pt-validate-status'));
  if (!d) return;
  await ptRefreshSession();
  ptRenderValidation(d);
}

async function ptFixScript() {
  if (!ptRequireCase()) return;
  const btn = document.getElementById('pt-fix-btn');
  btn.disabled = true;
  ptStatusEl('pt-validate-status').textContent = 'Asking LLM for a fix (this can take a few minutes)…';
  const d = await ptApi(`/fix_script/${ptCase.key}`, { method: 'POST' }, ptStatusEl('pt-validate-status'));
  btn.disabled = false;
  if (!d) return;
  await ptRefreshSession();
  ptStatusEl('pt-validate-status').textContent =
    `Revised (iteration ${d.iterations}); previous code archived. Review in 6. Generate, then re-run.`;
  goToPanel('panel-pt-gen');
}

// --- Testboxes (profiles CRUD) -----------------------------------------------------

async function renderPtTestboxPanel() {
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

// Fetch a stub tool router's /status message into a placeholder status element
async function loadToolStatus(apiName, elId) {
  const el = document.getElementById(elId);
  if (!el) return;
  try {
    const r = await fetch(`/api/${apiName}/status`);
    if (r.ok) {
      const d = await r.json();
      el.textContent = d.message || d.status || '';
    }
  } catch (_) { /* leave placeholder text when offline */ }
}

/** Merge new ATP rows into window.currentATP by id (prefer higher score / richer reason). */
function mergeATPCandidates(incoming, { precheckIds = null, source = 'search' } = {}) {
  const existing = window.currentATP || [];
  const byId = {};
  existing.forEach(c => { if (c && c.id) byId[c.id] = { ...c }; });
  (incoming || []).forEach(c => {
    if (!c || !c.id) return;
    const prev = byId[c.id];
    // Prefer longer/full descriptions when merging so search/suggest cannot re-truncate
    const prevDesc = (prev && prev.description) || '';
    const nextDesc = c.description || '';
    const betterDesc = (nextDesc.length >= prevDesc.length ? nextDesc : prevDesc)
      || c.reason || c.justification || prevDesc || '';
    const next = {
      id: c.id,
      title: c.title || (prev && prev.title) || c.id,
      description: betterDesc,
      justification: c.justification || c.reason || (prev && prev.justification) || '',
      score: c.score !== undefined ? c.score : (prev ? prev.score : 0.5),
      suite: c.suite || (prev && prev.suite) || '',
      source: c.source || source,
    };
    if (prev && (prev.score || 0) > (next.score || 0) && prev.source === 'llm') {
      // Keep higher LLM score but refresh reason/desc if richer
      byId[c.id] = {
        ...prev,
        title: (next.title && next.title.length < 120) ? next.title : (prev.title || next.title),
        justification: next.justification || prev.justification,
        description: betterDesc,
      };
    } else {
      byId[c.id] = next;
    }
  });
  const merged = Object.values(byId);
  merged.sort((a, b) => (Number(b.score) || 0) - (Number(a.score) || 0));
  window.currentATP = merged;

  const step3Sels = (currentSession && currentSession.step3 && currentSession.step3.selections) || [];
  // Preserve current checkbox state + optional precheck
  const checked = new Set();
  document.querySelectorAll('#atp-table input.atp-checkbox:checked').forEach(cb => checked.add(cb.dataset.id));
  if (precheckIds) precheckIds.forEach(id => checked.add(id));
  const fakeSels = Array.from(checked).map(id => ({ id_or_key: id }));
  const baseSels = fakeSels.length ? fakeSels : step3Sels;
  renderATPTable(merged, baseSels);
  // ensure prechecked
  if (precheckIds) {
    precheckIds.forEach(id => {
      const cb = document.querySelector(`#atp-table input.atp-checkbox[data-id="${id}"]`);
      if (cb) cb.checked = true;
    });
  }
}

function mergeTestLinkCandidates(incoming, { precheckIds = null, source = 'search' } = {}) {
  const existing = window.currentTestLink || [];
  const byId = {};
  existing.forEach(c => { if (c && c.id) byId[c.id] = { ...c }; });
  (incoming || []).forEach(c => {
    if (!c || !c.id) return;
    const prev = byId[c.id];
    const prevDesc = (prev && prev.description) || '';
    const nextDesc = c.description || c.snippet || '';
    // Prefer longer/full descriptions so search/suggest cannot re-truncate a rich load_case body
    const betterDesc = (nextDesc.length >= prevDesc.length ? nextDesc : prevDesc)
      || c.reason || (prev && prev.snippet) || '';
    byId[c.id] = {
      id: c.id,
      title: c.title || (prev && prev.title) || c.id,
      description: betterDesc,
      snippet: c.snippet || (prev && prev.snippet) || '',
      score: c.score !== undefined ? c.score : (prev ? prev.score : 0.6),
      source: c.source || source,
      justification: c.justification || c.reason || (prev && prev.justification) || '',
    };
  });
  const merged = Object.values(byId);
  merged.sort((a, b) => (Number(b.score) || 0) - (Number(a.score) || 0));
  window.currentTestLink = merged;
  const step1Sels = (currentSession && currentSession.step1 && currentSession.step1.selections) || [];
  const checked = new Set();
  document.querySelectorAll('#tl-table input.tl-checkbox:checked').forEach(cb => checked.add(cb.dataset.id));
  if (precheckIds) precheckIds.forEach(id => checked.add(id));
  const fakeSels = Array.from(checked).map(id => ({ id_or_key: id }));
  renderTestLinkTable(merged, fakeSels.length ? fakeSels : step1Sels);
  if (precheckIds) {
    precheckIds.forEach(id => {
      const cb = document.querySelector(`#tl-table input.tl-checkbox[data-id="${id}"]`);
      if (cb) cb.checked = true;
    });
  }
}

function mergeZephyrCandidates(incoming, { precheckIds = null, source = 'search' } = {}) {
  const existing = window.currentZephyr || [];
  const byKey = {};
  existing.forEach(c => {
    const k = c && (c.key || c.id);
    if (k) byKey[k] = { ...c, key: k };
  });
  (incoming || []).forEach(c => {
    const k = c && (c.key || c.id);
    if (!k) return;
    const prev = byKey[k];
    const prevDesc = (prev && prev.description) || '';
    const nextDesc = c.description || '';
    const betterDesc = (nextDesc.length >= prevDesc.length ? nextDesc : prevDesc)
      || c.reason || (prev && prev.title) || '';
    byKey[k] = {
      key: k,
      title: c.title || (prev && prev.title) || k,
      folder: c.folder || (prev && prev.folder) || '',
      description: betterDesc,
      justification: c.justification || c.reason || (prev && prev.justification) || '',
      score: c.score !== undefined ? c.score : (prev ? prev.score : 0.6),
      source: c.source || source,
    };
  });
  const merged = Object.values(byKey);
  merged.sort((a, b) => (Number(b.score) || 0) - (Number(a.score) || 0));
  window.currentZephyr = merged;
  const step2Sels = (currentSession && currentSession.step2 && currentSession.step2.selections) || [];
  const checked = new Set();
  document.querySelectorAll('#zephyr-table input.zephyr-checkbox:checked').forEach(cb => checked.add(cb.dataset.key));
  if (precheckIds) precheckIds.forEach(id => checked.add(id));
  const fakeSels = Array.from(checked).map(id => ({ id_or_key: id, key: id }));
  renderZephyrTable(merged, fakeSels.length ? fakeSels : step2Sels);
  if (precheckIds) {
    precheckIds.forEach(id => {
      const cb = document.querySelector(`#zephyr-table input.zephyr-checkbox[data-key="${id}"]`);
      if (cb) cb.checked = true;
    });
  }
}

async function searchTestLink() {
  const qEl = document.getElementById('tlSearchQ');
  const q = (qEl && qEl.value || '').trim();
  if (!q) {
    alert('Enter TestLink search keywords first.');
    return;
  }
  try {
    const res = await fetch('/api/wizard/search_testlink?q=' + encodeURIComponent(q));
    if (!res.ok) throw new Error('search failed ' + res.status);
    const data = await res.json();
    const results = (data.results || []).map(r => ({
      id: r.id,
      title: r.title,
      description: r.description || r.snippet || r.title || '',
      snippet: r.snippet || '',
      score: r.score != null ? r.score : 0.6,
      source: 'search',
      justification: r.justification || ('Matched search: ' + q),
    }));
    mergeTestLinkCandidates(results, { source: 'search' });
  } catch (e) {
    alert('TestLink search failed: ' + e);
  }
}

async function suggestTestLinkWithLLM() {
  if (!currentKey) {
    alert('Load a case first.');
    return;
  }
  const qEl = document.getElementById('tlSearchQ');
  const q = (qEl && qEl.value || '').trim();
  try {
    const res = await fetch('/api/wizard/suggest_testlink/' + encodeURIComponent(currentKey), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(q ? { q } : {}),
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(t.slice(0, 200) || ('status ' + res.status));
    }
    const data = await res.json();
    const suggestions = data.suggestions || [];
    const rows = suggestions.map(s => ({
      id: s.id,
      title: s.title || s.id,
      description: s.description || s.reason || '',
      justification: s.reason || 'LLM suggestion',
      score: s.score != null ? s.score : 0.85,
      source: 'llm',
    }));
    const ids = rows.map(r => r.id).filter(Boolean);
    mergeTestLinkCandidates(rows, { precheckIds: ids, source: 'llm' });
  } catch (e) {
    alert('Suggest TestLink with LLM failed: ' + e);
  }
}

async function searchZephyr() {
  const qEl = document.getElementById('zephyrSearchQ');
  const q = (qEl && qEl.value || '').trim();
  if (!q) {
    alert('Enter Zephyr search keywords first.');
    return;
  }
  try {
    let url = '/api/wizard/search_zephyr?q=' + encodeURIComponent(q);
    if (currentKey) url += '&case_key=' + encodeURIComponent(currentKey);
    const res = await fetch(url);
    if (!res.ok) throw new Error('search failed ' + res.status);
    const data = await res.json();
    const results = (data.results || []).map(r => ({
      key: r.key || r.id,
      title: r.title,
      folder: r.folder || '',
      description: r.description || r.title || '',
      justification: r.justification || ('Matched search: ' + q),
      score: r.score != null ? r.score : 0.6,
      source: 'search',
    }));
    mergeZephyrCandidates(results, { source: 'search' });
  } catch (e) {
    alert('Zephyr search failed: ' + e);
  }
}

async function suggestZephyrWithLLM() {
  if (!currentKey) {
    alert('Load a case first.');
    return;
  }
  const qEl = document.getElementById('zephyrSearchQ');
  const q = (qEl && qEl.value || '').trim();
  try {
    const res = await fetch('/api/wizard/suggest_zephyr/' + encodeURIComponent(currentKey), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(q ? { q } : {}),
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(t.slice(0, 200) || ('status ' + res.status));
    }
    const data = await res.json();
    const suggestions = data.suggestions || [];
    const rows = suggestions.map(s => ({
      key: s.key || s.id,
      title: s.title || s.id,
      folder: s.folder || '',
      description: s.description || s.reason || '',
      justification: s.reason || s.justification || 'LLM suggestion',
      score: s.score != null ? s.score : 0.85,
      source: 'llm',
    }));
    const ids = rows.map(r => r.key).filter(Boolean);
    mergeZephyrCandidates(rows, { precheckIds: ids, source: 'llm' });
  } catch (e) {
    alert('Suggest Zephyr with LLM failed: ' + e);
  }
}

async function searchATP() {
  const qEl = document.getElementById('atpSearchQ');
  const q = (qEl && qEl.value || '').trim();
  if (!q) {
    alert('Enter ATP search keywords first.');
    return;
  }
  try {
    const res = await fetch('/api/wizard/search_atp?q=' + encodeURIComponent(q));
    if (!res.ok) throw new Error('search failed ' + res.status);
    const data = await res.json();
    const results = (data.results || []).map(r => ({
      id: r.id,
      title: r.title || r.id,
      // Full analysis body from API (not the short title)
      description: r.description || '',
      suite: r.suite || '',
      score: r.score !== undefined ? r.score : 0.6,
      source: r.source || 'search',
      justification: 'Matched search: ' + q,
    }));
    mergeATPCandidates(results, { source: 'search' });
  } catch (e) {
    alert('ATP search failed: ' + e);
  }
}

async function suggestATPWithLLM() {
  if (!currentKey) {
    alert('Load a case first.');
    return;
  }
  const qEl = document.getElementById('atpSearchQ');
  const q = (qEl && qEl.value || '').trim();
  try {
    const res = await fetch('/api/wizard/suggest_atp/' + encodeURIComponent(currentKey), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(q ? { q } : {}),
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(t.slice(0, 200) || ('status ' + res.status));
    }
    const data = await res.json();
    const suggestions = data.suggestions || [];
    const rows = suggestions.map(s => ({
      id: s.id,
      title: s.title || s.id,
      description: s.description || '',
      justification: s.justification || s.reason || 'LLM suggestion',
      suite: s.suite || '',
      score: s.score !== undefined ? s.score : 0.85,
      source: 'llm',
    }));
    const ids = rows.map(r => r.id).filter(Boolean);
    mergeATPCandidates(rows, { precheckIds: ids, source: 'llm' });
  } catch (e) {
    alert('Suggest with LLM failed: ' + e);
  }
}

// Light / Dark mode toggle (aligned with design system)
(function() {
  const root = document.documentElement;
  const toggle = document.getElementById('theme-toggle');
  const icon = document.getElementById('theme-icon');

  function setTheme(theme) {
    if (theme === 'light') {
      root.classList.remove('dark');
      root.classList.add('light');
      if (icon) icon.textContent = '☀️';
    } else {
      root.classList.remove('light');
      root.classList.add('dark');
      if (icon) icon.textContent = '🌙';
    }
    localStorage.setItem('theme', theme);
  }

  // Initialize theme
  const saved = localStorage.getItem('theme');
  if (saved) {
    setTheme(saved);
  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
    setTheme('light');
  } else {
    setTheme('dark');
  }

  if (toggle) {
    toggle.addEventListener('click', () => {
      const isLight = root.classList.contains('light');
      setTheme(isLight ? 'dark' : 'light');
    });
  }
})();

// Keyboard activation for div[role="button"] nav items (Enter / Space), so
// sidebar navigation is usable without a mouse.
document.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter' && e.key !== ' ') return;
  const target = e.target;
  if (target instanceof HTMLElement && target.getAttribute('role') === 'button' && target.tabIndex >= 0) {
    e.preventDefault();
    target.click();
  }
});

// ============================================================================
// Delegated click dispatcher. Elements declare their handler declaratively:
//   data-action="fnName"            — top-level function to call
//   data-args='["panel-main", 1]'   — optional JSON array of arguments
// Works for static markup and for rows injected via innerHTML at runtime
// (no per-element listeners needed). Use dataArgs(...) to build data-args
// for runtime string values.
// ============================================================================
document.addEventListener('click', (e) => {
  const el = e.target.closest('[data-action]');
  if (!el) return;
  const fn = window[el.dataset.action];
  if (typeof fn !== 'function') {
    console.warn('data-action refers to unknown function:', el.dataset.action);
    return;
  }
  if (el.tagName === 'A') e.preventDefault();
  let args = [];
  if (el.dataset.args) {
    try {
      args = JSON.parse(el.dataset.args);
    } catch (err) {
      console.warn('Invalid data-args JSON on', el, err);
      return;
    }
  }
  fn.apply(el, args);
});

// Form-control bindings that were previously inline onchange/onkeydown attributes.
document.querySelectorAll('input[name="llmAuthMethod"]').forEach((radio) => {
  radio.addEventListener('change', updateAuthMethodUI);
});
{
  const q = document.getElementById('pt-search-q');
  if (q) q.addEventListener('keydown', (e) => { if (e.key === 'Enter') ptManualSearch(); });
  const fit = document.getElementById('pt-fit-decision');
  if (fit) fit.addEventListener('change', ptFitEdited);
  const prof = document.getElementById('pt-run-profile');
  if (prof) prof.addEventListener('change', function () { ptProfileSelected(this); });
}
