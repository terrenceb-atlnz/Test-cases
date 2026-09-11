// Shared candidate-table renderers (Generator + DB-search tools).
//
// Each review step (TestLink / Zephyr / ATPyLib) shows TWO tables:
//   • a top "candidates" table — search/suggest results, may be score-sorted;
//     ticking a row and clicking "Choose" moves it to the chosen table.
//   • a bottom "chosen" table — insertion-ordered (never auto-sorted); this is
//     the source of truth for Mark Reviewed + Confirmed. Ticking a row here and
//     clicking "Clear selected contents" moves it back up to the candidates.
//
// Chosen rows are held on the window.*Chosen bus (insertion-ordered arrays);
// the top table hides any candidate whose id is already chosen ("disappear
// from top"). See db-search.js for the choose/clear move actions and confirm
// reads the chosen arrays in generator.js.
import { S } from './state.js';
import { escapeHtml, truncateText } from './dom-helpers.js';

// Soft safety only for pathological megabyte fields (real TL/Zephyr bodies are typically < few KB)
const DESC_SOFT_MAX = 2000;

// Per-kind config: where the data/chosen buses live, the id field name, DOM ids,
// checkbox classes, and column layout. Keeps the three steps consistent.
export const TABLE_KINDS = {
  testlink: {
    idKey: 'id',
    dataBus: 'currentTestLink',
    chosenBus: 'currentTestLinkChosen',
    topEl: 'tl-table',
    chosenEl: 'tl-chosen-table',
    topCheckbox: 'tl-checkbox',
    chosenCheckbox: 'tl-chosen-checkbox',
    dataAttr: 'data-id',
    emptyTop: 'No TestLink candidates for this case.',
    emptyChosen: 'No cases chosen yet — tick rows above and click Choose.',
  },
  zephyr: {
    idKey: 'key',
    dataBus: 'currentZephyr',
    chosenBus: 'currentZephyrChosen',
    topEl: 'zephyr-table',
    chosenEl: 'zephyr-chosen-table',
    topCheckbox: 'zephyr-checkbox',
    chosenCheckbox: 'zephyr-chosen-checkbox',
    dataAttr: 'data-key',
    emptyTop: 'No relevant external Zephyr cross-refs found for this case.',
    emptyChosen: 'No cases chosen yet — tick rows above and click Choose.',
  },
  atp: {
    idKey: 'id',
    dataBus: 'currentATP',
    chosenBus: 'currentATPChosen',
    topEl: 'atp-table',
    chosenEl: 'atp-chosen-table',
    topCheckbox: 'atp-checkbox',
    chosenCheckbox: 'atp-chosen-checkbox',
    dataAttr: 'data-id',
    emptyTop: 'No ATPyLib candidates loaded for this case.',
    emptyChosen: 'No tests chosen yet — tick rows above and click Choose.',
  },
};

function chosenIdSet(kind) {
  const arr = window[TABLE_KINDS[kind].chosenBus] || [];
  return new Set(arr.map(c => c && c.id_or_key).filter(Boolean));
}

// -------- TestLink --------
function testlinkRowCells(c) {
  let descValue = c.description || c.snippet || c.title || '';
  descValue = truncateText(descValue, DESC_SOFT_MAX);
  const titleAttr = escapeHtml(descValue).replace(/"/g, '&quot;');
  const escapedDesc = escapeHtml(descValue).replace(/\n/g, '<br>');
  return `
        <td class="cell-id">${escapeHtml(c.id)}</td>
        <td class="cell-title">${escapeHtml(c.title || '')}</td>
        <td class="cell-score">${c.score ? Number(c.score).toFixed(2) : ''}</td>
        <td class="cell-description" title="${titleAttr}">${escapedDesc}</td>`;
}

export function renderTestLinkTable(cands) {
  const cont = document.getElementById('tl-table');
  const cfg = TABLE_KINDS.testlink;
  const chosen = chosenIdSet('testlink');
  const rows = (cands || []).filter(c => c && !chosen.has(c.id));
  if (!rows.length) {
    cont.innerHTML = (cands && cands.length)
      ? '<em>All candidates chosen — see below.</em>'
      : `<em>${cfg.emptyTop}</em>`;
    return;
  }
  let html = '<table class="table cols-5"><thead><tr><th></th><th>ID</th><th>Title</th><th>Score</th><th>Description</th></tr></thead><tbody>';
  rows.forEach(c => {
    html += `
      <tr>
        <td><input type="checkbox" class="${cfg.topCheckbox}" ${cfg.dataAttr}="${escapeHtml(c.id)}"></td>${testlinkRowCells(c)}
      </tr>`;
  });
  html += '</tbody></table>';
  cont.innerHTML = html;
}

// -------- Zephyr --------
function folderLeaf(folder) {
  if (!folder) return '';
  const parts = String(folder).replace(/\/+$/, '').split('/');
  return parts[parts.length - 1] || folder;
}

function zephyrRowCells(r) {
  const why = (r.justification || '').trim();
  let body = r.description || '';
  if (!body || body === r.title) body = r.description || r.title || why || '';
  const showWhy = why && body && body !== why && !body.includes(why.slice(0, Math.min(40, why.length)));
  const descValue = truncateText(body || why, DESC_SOFT_MAX);
  const score = (r.score !== undefined && r.score !== null) ? Number(r.score).toFixed(1) : '';
  const area = folderLeaf(r.folder);
  const whyLine = showWhy
    ? `<div class="justification-note">${escapeHtml(truncateText(why, DESC_SOFT_MAX))}</div>`
    : '';
  const titleAttr = escapeHtml((whyLine ? why + '\n' : '') + descValue).replace(/"/g, '&quot;');
  const escapedDesc = escapeHtml(descValue).replace(/\n/g, '<br>');
  return `
        <td class="cell-id">${escapeHtml(r.key)}</td>
        <td class="cell-title">${escapeHtml(r.title || '')}</td>
        <td class="cell-score">${score}</td>
        <td class="cell-folder" title="${escapeHtml(r.folder || '')}">${escapeHtml(area)}</td>
        <td class="cell-description" title="${titleAttr}">${whyLine}${escapedDesc}</td>`;
}

export function renderZephyrTable(refs) {
  const cont = document.getElementById('zephyr-table');
  const cfg = TABLE_KINDS.zephyr;
  const chosen = chosenIdSet('zephyr');
  const rows = (refs || []).filter(r => r && !chosen.has(r.key));
  if (!rows.length) {
    cont.innerHTML = (refs && refs.length)
      ? '<em>All candidates chosen — see below.</em>'
      : `<em>${cfg.emptyTop}</em>`;
    return;
  }
  let html = '<table class="table cols-6-zephyr"><thead><tr><th></th><th>Key</th><th>Title</th><th>Score</th><th>Area</th><th>Why / Description</th></tr></thead><tbody>';
  rows.forEach(r => {
    html += `
      <tr>
        <td><input type="checkbox" class="${cfg.topCheckbox}" ${cfg.dataAttr}="${escapeHtml(r.key)}"></td>${zephyrRowCells(r)}
      </tr>`;
  });
  html += '</tbody></table>';
  cont.innerHTML = html;
}

// -------- ATPyLib --------
/** Short title = first line / text before [analysis]; body = rest or full description. */
function splitAtpTitleDescription(title, description, fallbackId) {
  const full = String(description || title || '').trim();
  let shortTitle = String(title || '').trim();
  const br = shortTitle.indexOf('[');
  if (br > 0) shortTitle = shortTitle.substring(0, br).trim();
  if (!shortTitle || shortTitle === full) {
    const firstLine = full.split(/\n/)[0] || '';
    const m = full.match(/^([\s\S]*?)(?:\n\n?\[)/);
    shortTitle = (m ? m[1] : firstLine).trim().split('\n')[0].trim() || fallbackId || '';
  }
  let body = full;
  if (shortTitle && body.startsWith(shortTitle)) {
    body = body.slice(shortTitle.length).replace(/^\s*\n+/, '').trim() || full;
  }
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

function atpRowCells(c) {
  const sourceDesc = c.description || '';
  const { title: titleText, body: descBody } = splitAtpTitleDescription(c.title || '', sourceDesc, c.id || '');
  const just = (c.justification || c.reason || '').trim();
  let fullDesc = descBody;
  if (just && just.length > 8 && !fullDesc.includes(just.slice(0, Math.min(40, just.length)))) {
    if (!fullDesc || fullDesc.length < 60) fullDesc = just;
  }
  fullDesc = truncateText(fullDesc, DESC_SOFT_MAX);
  const score = (c.score !== undefined) ? Number(c.score).toFixed(2) : '';
  const suite = c.suite ? `<span class="cell-suite">(${escapeHtml(c.suite)})</span>` : '';
  const src = c.source || (c.justification && c.justification.indexOf('keyword') >= 0 ? 'keyword' : 'llm');
  const titleAttr = escapeHtml(fullDesc).replace(/"/g, '&quot;');
  const escapedDesc = escapeHtml(fullDesc).replace(/\n/g, '<br>');
  return `
        <td class="cell-id">${escapeHtml(c.id)}</td>
        <td class="cell-title">${escapeHtml(titleText)}${suite}</td>
        <td class="cell-score">${score}</td>
        <td class="cell-source">${escapeHtml(src)}</td>
        <td class="cell-description" title="${titleAttr}">${escapedDesc}</td>`;
}

export function renderATPTable(cands) {
  const cont = document.getElementById('atp-table');
  const cfg = TABLE_KINDS.atp;
  const chosen = chosenIdSet('atp');
  const rows = (cands || [])
    .filter(c => {
      const t = ((c.title || '') + (c.description || '') + (c.id || '')).toLowerCase();
      return !t.includes('(not a functional test)');
    })
    .filter(c => c && !chosen.has(c.id));
  if (!rows.length) {
    cont.innerHTML = (cands && cands.length)
      ? '<em>All candidates chosen — see below.</em>'
      : `<em>${cfg.emptyTop}</em>`;
    return;
  }
  let html = '<table class="table cols-6-atp"><thead><tr><th></th><th>ID</th><th>Title</th><th>Score</th><th>Src</th><th>Description</th></tr></thead><tbody>';
  rows.forEach(c => {
    html += `
      <tr>
        <td><input type="checkbox" class="${cfg.topCheckbox}" ${cfg.dataAttr}="${escapeHtml(c.id)}"></td>${atpRowCells(c)}
      </tr>`;
  });
  html += '</tbody></table>';
  cont.innerHTML = html;
}

// -------- Chosen table (shared) --------
// Renders window[chosenBus] in insertion order. Each stored entry keeps the full
// candidate object under `.record` so the same cell renderers can be reused.
const CHOSEN_CELLS = {
  testlink: (rec) => testlinkRowCells(rec),
  zephyr: (rec) => zephyrRowCells(rec),
  atp: (rec) => atpRowCells(rec),
};
const CHOSEN_HEAD = {
  testlink: '<th></th><th>ID</th><th>Title</th><th>Score</th><th>Description</th>',
  zephyr: '<th></th><th>Key</th><th>Title</th><th>Score</th><th>Area</th><th>Why / Description</th>',
  atp: '<th></th><th>ID</th><th>Title</th><th>Score</th><th>Src</th><th>Description</th>',
};
const CHOSEN_TABLE_CLASS = {
  testlink: 'cols-5',
  zephyr: 'cols-6-zephyr',
  atp: 'cols-6-atp',
};

export function renderChosenTable(kind) {
  const cfg = TABLE_KINDS[kind];
  const cont = document.getElementById(cfg.chosenEl);
  if (!cont) return;
  const chosen = window[cfg.chosenBus] || [];
  if (!chosen.length) {
    cont.innerHTML = `<em class="chosen-empty">${cfg.emptyChosen}</em>`;
    return;
  }
  const cells = CHOSEN_CELLS[kind];
  let html = `<table class="table ${CHOSEN_TABLE_CLASS[kind]} chosen-table"><thead><tr>${CHOSEN_HEAD[kind]}</tr></thead><tbody>`;
  chosen.forEach(entry => {
    const rec = entry.record || {};
    html += `
      <tr>
        <td><input type="checkbox" class="${cfg.chosenCheckbox}" ${cfg.dataAttr}="${escapeHtml(entry.id_or_key)}"></td>${cells(rec)}
      </tr>`;
  });
  html += '</tbody></table>';
  cont.innerHTML = html;
}

// Render both tables for a kind (top candidates + bottom chosen).
export function renderStepTables(kind, cands) {
  if (kind === 'testlink') renderTestLinkTable(cands);
  else if (kind === 'zephyr') renderZephyrTable(cands);
  else if (kind === 'atp') renderATPTable(cands);
  renderChosenTable(kind);
}
