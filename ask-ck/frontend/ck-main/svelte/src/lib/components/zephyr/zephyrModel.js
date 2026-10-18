// Zephyr Templating Tool — the pure model (ask-ck/plans/PLAN-zephyr-templating.md §5a).
// Carried over unchanged from the pre-Svelte zephyr-tool.js (2026-10-09, PLAN-test-composer
// Z1): the tree, the analysis's proposals, ticking, folding and the upload body. No DOM here, so
// the Svelte components and the specs share one copy. Tree rows are keyed by PATH ("P", "P/C",
// "P/C/T"), so a case listed in two cycles is two rows.

//@ts-nocheck

export const QUESTION_TITLES = {
  Q1: '1. Test plans cut (Test Strategy)',
  Q2: '2. Cycles not relevant',
  Q3: '3. Cases not relevant',
  Q4: '4. Not Mandatory / not Supported on first release (TPS)',
};

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

export function ancestors(id) {
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

/** Is a plan or cycle row open? The user's own fold wins; otherwise it opens only when the
 *  analysis unticked something INSIDE it (Terrence 2026-10-07: default-collapsed, "unless a change
 *  has been made within them by the LLM analysis"). */
export function isOpen(id, ai, folds) {
  if (folds && folds.has(id)) return folds.get(id);
  for (const k of ai.keys()) if (k.startsWith(id + '/')) return true;
  return false;
}

/** The rows on screen: a row shows only when every row above it is open. */
export function shownRows(tree, ai, folds) {
  return treeRows(tree).filter(r => !ancestors(r.id).some(a => !isOpen(a, ai, folds)));
}

/** "N cycle(s), M case(s), K unticked" for a plan or cycle row; '' for a case. */
export function rowCount(tree, row, ticked) {
  if (row.kind === 'case') return '';
  const below = treeRows(tree).filter(x => x.kind === 'case' && x.id.startsWith(row.id + '/'));
  const off = below.filter(x => !ticked.has(x.id)).length;
  const what = row.kind === 'plan' ? `${(row.item.cycles || []).length} cycle(s), ` : '';
  return `${what}${below.length} case(s)${off ? `, ${off} unticked` : ''}`;
}

/** "a/b plans · c/d cycles · e/f cases ticked" for the column head. */
export function tickSummary(tree, ticked) {
  const rows = treeRows(tree);
  const on = k => rows.filter(r => r.kind === k && ticked.has(r.id)).length;
  const all = k => rows.filter(r => r.kind === k).length;
  return `${on('plan')}/${all('plan')} plans · ${on('cycle')}/${all('cycle')} cycles · ${on('case')}/${all('case')} cases ticked`;
}

export function nameOf(tree, key) {
  const r = treeRows(tree).find(x => x.key === key);
  return r ? r.name || '' : '';
}

/** A field's value, or null when it is blank, `N/A`, `NA`, `None` or `-` (Terrence 2026-10-07:
 *  a project may have no team subfolder or no number). */
export function cleanField(v) {
  const t = String(v == null ? '' : v).trim();
  return ['', 'n/a', 'na', 'none', '-'].includes(t.toLowerCase()) ? null : t;
}

/** The Results Analysis column's data: the state line, sources, Q1–Q4, gaps, AI Notes and
 *  what went wrong (wiki problems, failed plan calls, refused proposals) — shown, never hidden. */
export function analysisView(job, tree) {
  if (!job) return null;
  const plans = job.plans || {};
  const slots = Object.values(plans);
  const done = slots.filter(s => ['done', 'error', 'skipped', 'stopped'].includes(s.state)).length;
  const stateText = {
    reading: 'Reading the wiki pages…',
    analysing: `Asking the model: ${done} of ${slots.length} plans answered${job.gaps && job.gaps.state === 'done' ? ', gaps done' : ''}…`,
    done: 'Analysis complete.', cancelled: 'Stopped — answers so far are kept.', error: 'The analysis failed.',
  }[job.state] || job.state;
  const pageNames = { tps: 'TPS', strategy: 'Test Strategy', feature: 'Feature Page' };
  const sources = job.pages
    ? Object.entries(job.pages).filter(([, p]) => p).map(([k, p]) => ({ label: pageNames[k] || k, url: p.url, title: p.title, exists: p.exists }))
    : null;
  const tpsRows = job.tps_rows ? ` TPS feature rows: ${job.tps_rows.sid} SID-style, ${job.tps_rows.prd} PRD-style, ${job.tps_rows.tested} tested.` : '';
  const all = slots.flatMap(s => s.deselect || []);
  const questions = Object.keys(QUESTION_TITLES).map(q => ({
    title: QUESTION_TITLES[q],
    items: all.filter(d => d.question === q).map(d => ({ key: d.key, name: nameOf(tree, d.key), reason: d.reason, source: d.source })),
  }));
  const g = job.gaps || {};
  const notes = (g.notes || []).map(n => n.note)
    .concat(Object.entries(plans).flatMap(([pk, s]) => (s.notes || []).map(n => `${n.key || pk}: ${n.note}`)));
  const problems = (job.wiki_problems || []).slice();
  for (const [pk, s] of Object.entries(plans)) {
    if (s.state === 'error') problems.push(`${pk}: the model call failed, so the whole plan stays ticked — ${s.error}`);
    if (s.state === 'stopped' || s.state === 'skipped') problems.push(`${pk}: stopped before it answered, so the whole plan stays ticked`);
    if ((s.dropped || []).length) problems.push(`${pk}: ${s.dropped.length} proposal(s) refused by the guardrail (${s.dropped.map(d => d.why).join('; ')})`);
  }
  if ((g.dropped || []).length) problems.push(`gaps: ${g.dropped.length} item(s) refused (${g.dropped.map(d => d.why).join('; ')})`);
  return {
    state: job.state, stateText, error: job.error || null,
    sources, featurePage: job.feature_page || '?', tpsRows,
    questions, isDone: job.state === 'done',
    gaps: { state: g.state, error: g.error, items: g.gaps || [] },
    notes, problems,
  };
}

/** The headline of the real upload's progress (GET /upload/run/{id}). */
export const RUN_HEADS = {
  running: 'Writing to Zephyr…', done: 'Upload complete.', refused: 'Refused — nothing was written.',
  stopped: 'Stopped at the first failure — nothing after it was written, and nothing was undone.',
  error: 'The upload tool failed.',
};