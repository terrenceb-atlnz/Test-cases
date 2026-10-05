// Zephyr Templating Tool — the single page (ask-ck/plans/PLAN-zephyr-templating.md §5a,
// docs/zephyr.txt "UI"). Paste a project's wiki URL → Organize with LLM → What Version / What
// Product fill in → two columns: Results Analysis (read-only) and the Plan → Cycle → Case tree
// (checkboxes) → Confirm un-greys API Upload, which shows the DRY-RUN call list (D9).
//
// One request, then polling (the browser connection ceiling): POST /analyse returns an id and
// GET /analyse/{id} is polled every POLL_MS. Tree rows are keyed by PATH ("P", "P/C", "P/C/T"),
// so a case listed in two cycles is two rows.
import { registerActions } from '../shared/actions.js';
import { escapeHtml, setButtonBusy, flashButtonDone } from '../shared/dom-helpers.js';

const ZT_API = '/api/zephyr-tool';
const POLL_MS = 2000;
const QUESTION_TITLES = {
  Q1: '1. Test plans cut (Test Strategy)',
  Q2: '2. Cycles not relevant',
  Q3: '3. Cases not relevant',
  Q4: '4. Not Mandatory / not Supported on first release (TPS)',
};

export const zt = {
  tree: null,          // GET /templates → snapshot
  job: null,           // the latest GET /analyse/{id}
  ticked: new Set(),   // row ids that are ticked
  ai: new Map(),       // row id → {question, reason, source} for rows the analysis unticked
  manual: [],          // [id, on] the user's own ticks, in order — replayed over each poll
  confirmed: false,
  poll: null,
  loaded: false,
};

// ------------------------------------------------------------------ tree model (pure)

/** Every row of the template tree: {id, kind, key, name, parent, depth, item}. */
export function treeRows(tree) {
  const rows = [];
  for (const p of (tree && tree.plans) || []) {
    rows.push({ id: p.key, kind: 'plan', key: p.key, name: p.name, parent: null, depth: 0, item: p });
    for (const c of p.cycles || []) {
      const cid = `${p.key}/${c.key}`;
      rows.push({ id: cid, kind: 'cycle', key: c.key, name: c.name, parent: p.key, depth: 1, item: c });
      for (const t of c.cases || []) {
        rows.push({ id: `${cid}/${t.key}`, kind: 'case', key: t.key, name: t.name, parent: cid, depth: 2, item: t });
      }
    }
  }
  return rows;
}

function descendants(rows, id) {
  return rows.filter(r => r.id.startsWith(id + '/')).map(r => r.id);
}

function ancestors(id) {
  const parts = id.split('/');
  const out = [];
  for (let i = 1; i < parts.length; i++) out.push(parts.slice(0, i).join('/'));
  return out;
}

/** Start with everything ticked, then untick what the analysis proposed (and everything below
 *  it). Returns {ticked, ai}. A case proposal applies to that case in every cycle of its plan. */
export function applyProposals(tree, job) {
  const rows = treeRows(tree);
  const ticked = new Set(rows.map(r => r.id));
  const ai = new Map();
  const plans = (job && job.plans) || {};
  for (const [planKey, slot] of Object.entries(plans)) {
    for (const d of (slot && slot.deselect) || []) {
      const hits = rows.filter(r => r.key === d.key && (r.id === planKey || r.id.startsWith(planKey + '/')));
      for (const r of hits) {
        ai.set(r.id, { question: d.question, reason: d.reason, source: d.source });
        ticked.delete(r.id);
        for (const k of descendants(rows, r.id)) ticked.delete(k);
      }
    }
  }
  return { ticked, ai };
}

/** Tick or untick one row: unticking unticks everything below it; ticking ticks everything below
 *  it and every row above it (a ticked case needs its cycle and plan). */
export function setTick(ticked, tree, id, on) {
  const rows = treeRows(tree);
  const ids = [id, ...descendants(rows, id)];
  if (on) {
    ids.forEach(k => ticked.add(k));
    ancestors(id).forEach(k => ticked.add(k));
  } else {
    ids.forEach(k => ticked.delete(k));
  }
  return ticked;
}

/** The /upload/preview body: the ticked plans, each with ALL its template cycles (an unticked
 *  cycle still has to be unlinked from the new plan) marked selected or not, and each selected
 *  cycle's unticked cases as `excluded`. */
export function uploadSelection(tree, ticked, project) {
  const plans = [];
  for (const p of (tree && tree.plans) || []) {
    if (!ticked.has(p.key)) continue;
    plans.push({
      key: p.key, name: p.name,
      cycles: (p.cycles || []).map(c => {
        const cid = `${p.key}/${c.key}`;
        return { key: c.key, name: c.name, selected: ticked.has(cid),
                 excluded: (c.cases || []).filter(t => !ticked.has(`${cid}/${t.key}`)).map(t => t.key) };
      }),
    });
  }
  return { version: project.version || null, middle: project.middle || null,
           product: project.product || null, number: project.number || null, plans };
}

// ------------------------------------------------------------------ rendering (pure)

export function renderTree(tree, ticked, ai) {
  const rows = treeRows(tree);
  if (!rows.length) return '<div class="zt-empty">No templates imported yet — use Refresh templates.</div>';
  return rows.map(r => {
    const on = ticked.has(r.id);
    const why = ai.get(r.id);
    const count = r.kind === 'plan' ? ` <span class="zt-count">${(r.item.cycles || []).length} cycle(s)</span>`
      : r.kind === 'cycle' ? ` <span class="zt-count">${(r.item.cases || []).length} case(s)</span>` : '';
    return `<div class="zt-row zt-${r.kind}${on ? '' : ' is-off'}" style="--zt-depth:${r.depth}">`
      + `<label><input type="checkbox" data-action="ztToggle" data-id="${escapeHtml(r.id)}"${on ? ' checked' : ''}>`
      + ` <span class="zt-key">${escapeHtml(r.key)}</span> ${escapeHtml(r.name || '')}${count}</label>`
      + (why ? `<div class="zt-why"><b>${escapeHtml(why.question)}</b> ${escapeHtml(why.reason)}`
        + ` <span class="zt-source">— ${escapeHtml(why.source)}</span></div>` : '')
      + '</div>';
  }).join('');
}

function nameOf(tree, key) {
  const r = treeRows(tree).find(x => x.key === key);
  return r ? r.name || '' : '';
}

/** The read-only Results Analysis column: Q1–Q4 proposals, 5. Gaps, 6. AI Notes, then what went
 *  wrong (wiki problems, failed plan calls, refused proposals). */
export function renderAnalysis(job, tree) {
  if (!job) return '<div class="zt-empty">Paste a project page URL and press Organize with LLM.</div>';
  const out = [];
  const plans = job.plans || {};
  const slots = Object.values(plans);
  const done = slots.filter(s => ['done', 'error', 'skipped'].includes(s.state)).length;
  const stateText = {
    reading: 'Reading the wiki pages…',
    analysing: `Asking the model: ${done} of ${slots.length} plans answered${job.gaps && job.gaps.state === 'done' ? ', gaps done' : ''}…`,
    done: 'Analysis complete.', cancelled: 'Stopped — answers so far are kept.', error: 'The analysis failed.',
  }[job.state] || job.state;
  out.push(`<div class="zt-state zt-state-${escapeHtml(job.state)}">${escapeHtml(stateText)}</div>`);
  if (job.error) out.push(`<div class="zt-problem">${escapeHtml(job.error)}</div>`);
  if (job.pages) {
    const pg = Object.entries(job.pages).map(([k, p]) => p
      ? `<li>${escapeHtml({ tps: 'TPS', strategy: 'Test Strategy', feature: 'Feature Page' }[k] || k)}: `
        + `<a href="${escapeHtml(p.url)}" target="_blank" rel="noopener">${escapeHtml(p.title)}</a>`
        + `${p.exists ? '' : ' (not created)'}</li>` : '').join('');
    const rowsTxt = job.tps_rows ? ` TPS feature rows: ${job.tps_rows.sid} SID-style, ${job.tps_rows.prd} PRD-style, ${job.tps_rows.tested} tested.` : '';
    out.push(`<div class="zt-block"><div class="zt-h">Sources</div><ul>${pg}</ul>`
      + `<div class="zt-small">Feature Page: ${escapeHtml(job.feature_page || '?')}.${escapeHtml(rowsTxt)}</div></div>`);
  }
  const all = slots.flatMap(s => s.deselect || []);
  for (const q of Object.keys(QUESTION_TITLES)) {
    const items = all.filter(d => d.question === q);
    out.push(`<div class="zt-block"><div class="zt-h">${escapeHtml(QUESTION_TITLES[q])} <span class="zt-count">${items.length}</span></div>`
      + (items.length ? '<ul>' + items.map(d => `<li><span class="zt-key">${escapeHtml(d.key)}</span> `
        + `${escapeHtml(nameOf(tree, d.key))} — ${escapeHtml(d.reason)} <span class="zt-source">(${escapeHtml(d.source)})</span></li>`).join('') + '</ul>'
        : `<div class="zt-small">${job.state === 'done' ? 'None.' : '…'}</div>`) + '</div>');
  }
  const g = job.gaps || {};
  out.push(`<div class="zt-block"><div class="zt-h">5. Gaps — required, no template <span class="zt-count">${(g.gaps || []).length}</span></div>`
    + (g.state === 'error' ? `<div class="zt-problem">${escapeHtml(g.error)}</div>` : '')
    + ((g.gaps || []).length ? '<ul>' + g.gaps.map(x => `<li>${escapeHtml(x.requirement)} <span class="zt-source">(${escapeHtml(x.source)})</span>`
      + `${x.why ? ' — ' + escapeHtml(x.why) : ''}</li>`).join('') + '</ul>'
      : `<div class="zt-small">${g.state === 'done' ? 'None found.' : g.state === 'error' ? '' : '…'}</div>`) + '</div>');
  const notes = (g.notes || []).map(n => n.note)
    .concat(Object.entries(plans).flatMap(([pk, s]) => (s.notes || []).map(n => `${n.key || pk}: ${n.note}`)));
  out.push(`<div class="zt-block"><div class="zt-h">6. AI Notes <span class="zt-count">${notes.length}</span></div>`
    + (notes.length ? '<ul>' + notes.map(n => `<li>${escapeHtml(n)}</li>`).join('') + '</ul>' : '<div class="zt-small">…</div>') + '</div>');
  const probs = (job.wiki_problems || []).slice();
  for (const [pk, s] of Object.entries(plans)) {
    if (s.state === 'error') probs.push(`${pk}: the model call failed, so the whole plan stays ticked — ${s.error}`);
    if ((s.dropped || []).length) probs.push(`${pk}: ${s.dropped.length} proposal(s) refused by the guardrail (${s.dropped.map(d => d.why).join('; ')})`);
  }
  if ((g.dropped || []).length) probs.push(`gaps: ${g.dropped.length} item(s) refused (${g.dropped.map(d => d.why).join('; ')})`);
  if (probs.length) {
    out.push(`<div class="zt-block"><div class="zt-h">Check these <span class="zt-count">${probs.length}</span></div><ul>`
      + probs.map(p => `<li>${escapeHtml(p)}</li>`).join('') + '</ul></div>');
  }
  return out.join('');
}

export function renderUpload(d) {
  const t = d.targets || {};
  const head = `<div class="zt-h">API Upload — dry run (nothing was written)</div>`
    + `<div class="zt-small">Plan folder: ${escapeHtml((t.testplan && t.testplan.path) || 'not found')} · `
    + `Cycle folder: ${escapeHtml((t.testrun && t.testrun.path) || 'not found')} · `
    + `${d.counts.calls} calls, ${d.counts.writes_not_captured} not captured yet.</div>`
    + ((d.problems || []).length ? '<ul>' + d.problems.map(p => `<li class="zt-problem">${escapeHtml(p)}</li>`).join('') + '</ul>' : '');
  const rows = (d.calls || []).map(c => `<tr class="${c.known ? '' : 'zt-unknown'}"><td>${c.n}</td><td>${escapeHtml(c.op)}</td>`
    + `<td><code>${escapeHtml(c.method)} ${escapeHtml(c.path)}</code></td><td>${escapeHtml(c.about)}</td>`
    + `<td>${c.known ? 'known' : 'not captured'}</td></tr>`).join('');
  return head + `<table class="table zt-calls"><thead><tr><th>#</th><th>step</th><th>call</th><th>what</th><th>request</th></tr></thead><tbody>${rows}</tbody></table>`;
}

// ------------------------------------------------------------------ page

function el(id) { return document.getElementById(id); }

function setStatus(msg, bad) {
  const s = el('zt-status');
  if (!s) return;
  s.textContent = msg || '';
  s.classList.toggle('is-bad', !!bad);
}

async function api(path, opts = {}) {
  const r = await fetch(ZT_API + path, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts));
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    const det = d.detail;
    throw new Error(typeof det === 'string' ? det : det && det.error ? det.error : `HTTP ${r.status}`);
  }
  return d;
}

function project() {
  return {
    version: (el('zt-version') || {}).value || '',
    product: (el('zt-product') || {}).value || '',
    middle: (zt.job && zt.job.project && zt.job.project.middle) || null,
    number: (zt.job && zt.job.project && zt.job.project.number) || null,
  };
}

function setConfirmed(on) {
  zt.confirmed = on;
  const up = el('zt-upload');
  if (up) up.disabled = !on;
  const cf = el('zt-confirm');
  if (cf) cf.textContent = on ? 'Confirmed ✓' : 'Confirm';
}

function paint() {
  const a = el('zt-analysis');
  if (a) a.innerHTML = renderAnalysis(zt.job, zt.tree);
  const t = el('zt-tree');
  if (t) t.innerHTML = renderTree(zt.tree, zt.ticked, zt.ai);
  const n = el('zt-tree-count');
  if (n) {
    const rows = treeRows(zt.tree);
    const on = k => rows.filter(r => r.kind === k && zt.ticked.has(r.id)).length;
    const all = k => rows.filter(r => r.kind === k).length;
    n.textContent = `${on('plan')}/${all('plan')} plans · ${on('cycle')}/${all('cycle')} cycles · ${on('case')}/${all('case')} cases ticked`;
  }
}

async function loadTree() {
  const d = await api('/templates');
  zt.tree = d.snapshot;
  zt.ticked = new Set(treeRows(zt.tree).map(r => r.id));
  zt.ai = new Map();
  zt.manual = [];
  const info = el('zt-templates-info');
  if (info) {
    const c = (zt.tree && zt.tree.counts) || {};
    info.textContent = zt.tree
      ? `Templates imported ${String(zt.tree.imported_at || '').slice(0, 16).replace('T', ' ')} UTC: ${c.plans} plans, ${c.cycles} cycles, ${c.cases} cases.`
      : 'No templates imported yet.';
  }
}

/** Called by nav.js whenever the panel is shown. Loads the template tree once. */
export async function renderZtPanel() {
  if (!zt.loaded) {
    zt.loaded = true;
    try { await loadTree(); } catch (e) { setStatus('Could not load the templates: ' + e.message, true); }
  }
  paint();
}

function stopPolling() {
  if (zt.poll) { clearInterval(zt.poll); zt.poll = null; }
  const c = el('zt-cancel');
  if (c) c.classList.add('hidden');
}

function fillProject(p) {
  if (!p) return;
  const v = el('zt-version'), pr = el('zt-product'), note = el('zt-version-note');
  if (v && !v.dataset.touched) v.value = p.version || '';
  if (pr && !pr.dataset.touched) pr.value = p.product || '';
  if (note) {
    note.textContent = p.version
      ? `from the ${p.version_source}${p.project_version ? ` — the project page says ${p.project_version}` : ''}` : '';
  }
}

async function pollOnce(id) {
  let d;
  try { d = await api('/analyse/' + encodeURIComponent(id)); } catch (e) {
    stopPolling(); setStatus(e.message, true); return;
  }
  zt.job = d;
  fillProject(d.project);
  rebuildTicks();
  setConfirmed(false);
  paint();
  if (['done', 'error', 'cancelled'].includes(d.state)) {
    stopPolling();
    const btn = el('zt-analyse');
    setButtonBusy(btn, false);
    flashButtonDone(btn, d.state === 'done');
    setStatus(d.state === 'done' ? 'Review the ticks, then Confirm.' : '', d.state === 'error');
  }
}

async function ztAnalyse() {
  const url = ((el('zt-url') || {}).value || '').trim();
  if (!url) { setStatus('Paste the project page URL first.', true); return; }
  if (!zt.tree) { setStatus('No templates imported yet — Refresh templates first.', true); return; }
  const btn = el('zt-analyse');
  if (!setButtonBusy(btn, true, { label: 'Organizing…' })) return;
  stopPolling();
  zt.manual = [];
  ['zt-version', 'zt-product'].forEach(i => { const x = el(i); if (x) delete x.dataset.touched; });
  el('zt-upload-result') && (el('zt-upload-result').innerHTML = '');
  setStatus('');
  try {
    const { id } = await api('/analyse', { method: 'POST', body: JSON.stringify({ url }) });
    zt.job = { id, state: 'reading', plans: {} };
    paint();
    const c = el('zt-cancel');
    if (c) { c.classList.remove('hidden'); c.dataset.args = JSON.stringify([id]); }
    zt.poll = setInterval(() => pollOnce(id), POLL_MS);
  } catch (e) {
    setButtonBusy(btn, false);
    flashButtonDone(btn, false);
    setStatus(e.message, true);
  }
}

async function ztCancel(id) {
  try { await api('/analyse/' + encodeURIComponent(id) + '/cancel', { method: 'POST' }); } catch (e) { setStatus(e.message, true); }
}

/** The analysis's ticks, then the user's own changes on top (a poll must not undo a click). */
function rebuildTicks() {
  const f = applyProposals(zt.tree, zt.job);
  zt.ticked = f.ticked;
  zt.ai = f.ai;
  for (const [id, on] of zt.manual) setTick(zt.ticked, zt.tree, id, on);
}

function ztToggle() {
  const id = this.dataset.id;
  zt.manual.push([id, this.checked]);
  setTick(zt.ticked, zt.tree, id, this.checked);
  setConfirmed(false);
  paint();
}

function ztConfirm() {
  if (!zt.tree) return;
  const sel = uploadSelection(zt.tree, zt.ticked, project());
  if (!sel.plans.length) { setStatus('Nothing is ticked.', true); return; }
  setConfirmed(true);
  setStatus(`Confirmed: ${sel.plans.length} plan(s). API Upload shows what it would do — nothing is written yet.`);
}

async function ztUpload() {
  if (!zt.confirmed) return;
  const btn = el('zt-upload');
  if (!setButtonBusy(btn, true, { label: 'Preparing…' })) return;
  let ok = false;
  try {
    const d = await api('/upload/preview', { method: 'POST', body: JSON.stringify(uploadSelection(zt.tree, zt.ticked, project())) });
    el('zt-upload-result').innerHTML = renderUpload(d);
    ok = true;
  } catch (e) {
    setStatus(e.message, true);
  } finally {
    setButtonBusy(btn, false);
    flashButtonDone(btn, ok);
  }
}

async function ztRefreshTemplates() {
  const btn = this instanceof HTMLElement ? this : el('zt-refresh');
  if (!setButtonBusy(btn, true, { label: 'Reading Zephyr…' })) return;
  let ok = false;
  try {
    const d = await api('/templates/refresh', { method: 'POST' });
    await loadTree();
    zt.manual = [];
    if (zt.job) rebuildTicks();
    setConfirmed(false);
    paint();
    setStatus(`Templates refreshed: ${d.written ? d.written.plans + ' plans' : 'done'}.`);
    ok = true;
  } catch (e) {
    setStatus(e.message, true);
  } finally {
    setButtonBusy(btn, false);
    flashButtonDone(btn, ok);
  }
}

document.addEventListener('input', (e) => {
  const t = e.target;
  if (t instanceof HTMLElement && (t.id === 'zt-version' || t.id === 'zt-product')) {
    t.dataset.touched = '1';
    setConfirmed(false);
  }
});

registerActions({ ztAnalyse, ztCancel, ztToggle, ztConfirm, ztUpload, ztRefreshTemplates });
