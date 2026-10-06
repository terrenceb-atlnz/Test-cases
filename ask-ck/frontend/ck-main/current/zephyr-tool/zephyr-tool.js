// Zephyr Templating Tool — the single page (ask-ck/plans/PLAN-zephyr-templating.md §5a,
// docs/zephyr.txt "UI"). Paste a project's wiki URL → Organize with LLM → What Version / What
// Product fill in → two columns: Results Analysis (read-only) and the Plan → Cycle → Case tree
// (checkboxes) → Confirm un-greys API Upload, which shows the call list (D9) and where the project
// has folders in every version → typing the product AND the version un-greys Write to Zephyr
// (§5b P6), the real upload, polled like the analysis.
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
  folds: new Map(),    // row id → open? — the user's own folds; unset rows follow isOpen()'s default
  confirmed: false,
  previewed: null,     // the selection API Upload listed — the one Write to Zephyr sends
  run: null,           // the latest GET /upload/run/{id}
  runPoll: null,
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

/** Is a plan or cycle row open? The user's own fold wins; otherwise it opens only when the
 *  analysis unticked something INSIDE it (Terrence 2026-10-07: default-collapsed, "unless a change
 *  has been made within them by the LLM analysis"). */
export function isOpen(id, ai, folds) {
  if (folds && folds.has(id)) return folds.get(id);
  for (const k of ai.keys()) if (k.startsWith(id + '/')) return true;
  return false;
}

export function renderTree(tree, ticked, ai, folds = new Map()) {
  const rows = treeRows(tree);
  if (!rows.length) return '<div class="zt-empty">No templates imported yet — use Refresh templates.</div>';
  const shown = rows.filter(r => !ancestors(r.id).some(a => !isOpen(a, ai, folds)));
  return shown.map(r => {
    const on = ticked.has(r.id);
    const why = ai.get(r.id);
    let count = '';
    if (r.kind !== 'case') {
      const below = rows.filter(x => x.kind === 'case' && x.id.startsWith(r.id + '/'));
      const off = below.filter(x => !ticked.has(x.id)).length;
      const what = r.kind === 'plan' ? `${(r.item.cycles || []).length} cycle(s), ` : '';
      count = ` <span class="zt-count">${what}${below.length} case(s)${off ? `, ${off} unticked` : ''}</span>`;
    }
    const open = r.kind !== 'case' && isOpen(r.id, ai, folds);
    const fold = r.kind === 'case' ? '<span class="zt-fold-pad"></span>'
      : `<button type="button" class="zt-fold" data-action="ztFold" data-id="${escapeHtml(r.id)}" aria-expanded="${open}"`
        + ` aria-label="${open ? 'Collapse' : 'Expand'} ${escapeHtml(r.key)}">${open ? '▾' : '▸'}</button>`;
    return `<div class="zt-row zt-${r.kind}${on ? '' : ' is-off'}" style="--zt-depth:${r.depth}">`
      + fold
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
  const done = slots.filter(s => ['done', 'error', 'skipped', 'stopped'].includes(s.state)).length;
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
    if (s.state === 'stopped' || s.state === 'skipped') probs.push(`${pk}: stopped before it answered, so the whole plan stays ticked`);
    if ((s.dropped || []).length) probs.push(`${pk}: ${s.dropped.length} proposal(s) refused by the guardrail (${s.dropped.map(d => d.why).join('; ')})`);
  }
  if ((g.dropped || []).length) probs.push(`gaps: ${g.dropped.length} item(s) refused (${g.dropped.map(d => d.why).join('; ')})`);
  if (probs.length) {
    out.push(`<div class="zt-block"><div class="zt-h">Check these <span class="zt-count">${probs.length}</span></div><ul>`
      + probs.map(p => `<li>${escapeHtml(p)}</li>`).join('') + '</ul></div>');
  }
  return out.join('');
}

/** True when the typed product and version equal the previewed selection's (§5b P6). */
export function confirmMatches(sel, product, version) {
  return !!(sel && sel.product && sel.version
    && (product || '').trim() === sel.product && (version || '').trim() === sel.version);
}

/** The API Upload result: where the project has folders in EVERY version (a project that slipped
 *  a release can carry an old version — P6), what is skipped (D15), the calls, and — when nothing
 *  stands in the way — the Write to Zephyr box. */
export function renderUpload(d, sel) {
  const t = d.targets || {};
  const c = d.counts || {};
  const version = (sel && sel.version) || '';
  const out = [`<div class="zt-h">API Upload — what it will do (nothing is written yet)</div>`
    + `<div class="zt-small">Plan folder: ${escapeHtml((t.testplan && t.testplan.path) || 'not found')} · `
    + `Cycle folder: ${escapeHtml((t.testrun && t.testrun.path) || 'not found')} · `
    + `${c.plans || 0} plan(s), ${c.cycles || 0} cycle(s), ${c.calls || 0} calls`
    + `${c.skipped ? `, ${c.skipped} skipped` : ''}.</div>`];
  const folders = d.project_folders || [];
  const other = folders.filter(f => f.version !== version);
  out.push(`<div class="zt-block"><div class="zt-h">Where ${escapeHtml((sel && sel.product) || 'the project')} has folders in Zephyr</div>`
    + (folders.length ? '<ul>' + folders.map(f => `<li class="${f.version !== version ? 'zt-problem' : ''}">`
      + `${f.kind === 'testplan' ? 'plans' : 'cycles'}: ${escapeHtml(f.path)}`
      + `${f.version !== version ? ` — a different version from What Version (${escapeHtml(version)})` : ''}</li>`).join('') + '</ul>'
      : '<div class="zt-small">None found.</div>')
    + (other.length ? `<div class="zt-small zt-problem">Check What Version: if the project slipped a release, the wiki may still name the old one.</div>` : '')
    + '</div>');
  if ((d.duplicates || []).length) {
    out.push(`<div class="zt-block"><div class="zt-h">Skipped — already in the project folder</div><ul>`
      + d.duplicates.map(x => `<li><span class="zt-key">${escapeHtml(x.key)}</span> → ${escapeHtml(x.name)} exists</li>`).join('') + '</ul></div>');
  }
  if ((d.problems || []).length) {
    out.push('<ul>' + d.problems.map(p => `<li class="zt-problem">${escapeHtml(p)}</li>`).join('') + '</ul>');
  }
  const rows = (d.calls || []).map(x => `<tr class="${x.known ? '' : 'zt-unknown'}"><td>${x.n}</td><td>${escapeHtml(x.op)}</td>`
    + `<td><code>${escapeHtml(x.method)} ${escapeHtml(x.path)}</code></td><td>${escapeHtml(x.about)}</td></tr>`).join('');
  out.push(`<table class="table zt-calls"><thead><tr><th>#</th><th>step</th><th>call</th><th>what</th></tr></thead><tbody>${rows}</tbody></table>`);
  if (!(d.problems || []).length && (d.calls || []).length && sel) {
    out.push(`<div class="zt-block zt-run"><div class="zt-h">Write to Zephyr</div>`
      + `<div class="zt-small">This makes the changes above in Zephyr. To confirm, type the product and the AW+ version `
      + `exactly as shown — and check the version is still right for this project.</div>`
      + `<div class="zt-line"><input id="zt-run-product" class="form-input" autocomplete="off" aria-label="Type the product to confirm" placeholder="type ${escapeHtml(sel.product || '')}">`
      + `<input id="zt-run-version" class="form-input" autocomplete="off" aria-label="Type the AW+ version to confirm" placeholder="type ${escapeHtml(sel.version || '')}">`
      + `<button id="zt-run" class="btn btn-primary" data-action="ztRun" disabled>Write to Zephyr</button></div>`
      + `<div id="zt-run-result"></div></div>`);
  }
  return out.join('');
}

/** The real upload's progress and outcome (GET /upload/run/{id}). */
export function renderRun(job) {
  if (!job) return '';
  const res = job.result || {};
  const head = {
    running: 'Writing to Zephyr…', done: 'Upload complete.', refused: 'Refused — nothing was written.',
    stopped: 'Stopped at the first failure — nothing after it was written, and nothing was undone.',
    error: 'The upload tool failed.',
  }[job.state] || job.state;
  const out = [`<div class="zt-state zt-state-${escapeHtml(job.state)}">${escapeHtml(head)}</div>`];
  const err = job.error || res.error;
  if (err) out.push(`<div class="zt-problem">${escapeHtml(err)}</div>`);
  if (res.stopped_at) out.push(`<div class="zt-small">Stopped in ${escapeHtml(res.stopped_at)}.</div>`);
  if ((res.created || []).length) {
    out.push(`<div class="zt-small">Created in Zephyr: ${res.created.map(x => `${escapeHtml(x.kind)} ${escapeHtml(String(x.id))} (from ${escapeHtml(x.from || '')})`).join(', ')}.</div>`);
  }
  if ((res.skipped || []).length) out.push(`<div class="zt-small">Skipped: ${res.skipped.map(x => escapeHtml(x.key)).join(', ')}.</div>`);
  out.push('<ol class="zt-steps">' + (job.steps || []).map(x => `<li>${escapeHtml(x.msg || '')}</li>`).join('') + '</ol>');
  return out.join('');
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
  if (!on && !zt.run) {                     // the selection changed: the listed calls no longer apply
    zt.previewed = null;
    const r = el('zt-upload-result');
    if (r) r.innerHTML = '';
  }
  const up = el('zt-upload');
  if (up) up.disabled = !on;
  const cf = el('zt-confirm');
  if (cf) cf.textContent = on ? 'Confirmed ✓' : 'Confirm';
}

function paint() {
  const a = el('zt-analysis');
  if (a) a.innerHTML = renderAnalysis(zt.job, zt.tree);
  const t = el('zt-tree');
  if (t) t.innerHTML = renderTree(zt.tree, zt.ticked, zt.ai, zt.folds);
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
  zt.folds = new Map();
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
  if (c) { c.classList.add('hidden'); c.disabled = false; c.textContent = 'Stop'; }
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
  zt.folds = new Map();
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
  const c = el('zt-cancel');
  if (c) { c.disabled = true; c.textContent = 'Stopping…'; }
  try {
    await api('/analyse/' + encodeURIComponent(id) + '/cancel', { method: 'POST' });
    setStatus('Stopping — the calls with the model are being cancelled.');
  } catch (e) {
    setStatus(e.message, true);
    if (c) { c.disabled = false; c.textContent = 'Stop'; }
  }
}

/** The analysis's ticks, then the user's own changes on top (a poll must not undo a click). */
function rebuildTicks() {
  const f = applyProposals(zt.tree, zt.job);
  zt.ticked = f.ticked;
  zt.ai = f.ai;
  for (const [id, on] of zt.manual) setTick(zt.ticked, zt.tree, id, on);
}

/** Open or close one plan or cycle (the arrow beside it). */
function ztFold() {
  const id = this.dataset.id;
  zt.folds.set(id, !isOpen(id, zt.ai, zt.folds));
  paint();
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
    const sel = uploadSelection(zt.tree, zt.ticked, project());
    const d = await api('/upload/preview', { method: 'POST', body: JSON.stringify(sel) });
    zt.previewed = sel;
    zt.run = null;
    el('zt-upload-result').innerHTML = renderUpload(d, sel);
    ok = true;
  } catch (e) {
    setStatus(e.message, true);
  } finally {
    setButtonBusy(btn, false);
    flashButtonDone(btn, ok);
  }
}

function stopRunPolling() {
  if (zt.runPoll) { clearInterval(zt.runPoll); zt.runPoll = null; }
}

async function pollRun(id) {
  let d;
  try { d = await api('/upload/run/' + encodeURIComponent(id)); } catch (e) {
    stopRunPolling(); setStatus(e.message, true); return;
  }
  zt.run = d;
  const box = el('zt-run-result');
  if (box) box.innerHTML = renderRun(d);
  if (d.state !== 'running') {
    stopRunPolling();
    setStatus(d.state === 'done' ? 'Upload complete.' : 'The upload did not complete — see below.', d.state !== 'done');
  }
}

/** The real upload of exactly the selection API Upload listed (§5b). */
async function ztRun() {
  const sel = zt.previewed;
  const product = (el('zt-run-product') || {}).value || '';
  const version = (el('zt-run-version') || {}).value || '';
  if (!confirmMatches(sel, product, version)) return;
  const btn = el('zt-run');
  if (btn) btn.disabled = true;
  ['zt-run-product', 'zt-run-version'].forEach(i => { const x = el(i); if (x) x.disabled = true; });
  try {
    const { id } = await api('/upload/run', { method: 'POST',
      body: JSON.stringify(Object.assign({}, sel, { confirm_product: product.trim(), confirm_version: version.trim() })) });
    zt.run = { id, state: 'running', steps: [] };
    el('zt-run-result').innerHTML = renderRun(zt.run);
    stopRunPolling();
    zt.runPoll = setInterval(() => pollRun(id), POLL_MS);
  } catch (e) {
    setStatus(e.message, true);
    if (btn) btn.disabled = false;
    ['zt-run-product', 'zt-run-version'].forEach(i => { const x = el(i); if (x) x.disabled = false; });
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
  if (t instanceof HTMLElement && (t.id === 'zt-run-product' || t.id === 'zt-run-version')) {
    const b = el('zt-run');
    if (b) b.disabled = !confirmMatches(zt.previewed, (el('zt-run-product') || {}).value, (el('zt-run-version') || {}).value);
  }
});

registerActions({ ztAnalyse, ztCancel, ztToggle, ztFold, ztConfirm, ztUpload, ztRun, ztRefreshTemplates });
