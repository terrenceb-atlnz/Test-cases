// Chosen-list mechanics for the two-table review pattern (TestLink/Zephyr/ATP).
//
// Each step keeps an insertion-ordered array on window.<chosenBus>, whose
// entries are { id_or_key, title, justification, order, record } — `record` is
// the full candidate object so the chosen table reuses the same cell renderers.
// The top ("candidates") table hides any id already present here; the bottom
// ("chosen") table renders these in order. Confirm reads these arrays.
import { S } from './state.js';
import { registerActions } from './actions.js';
import { TABLE_KINDS, renderStepTables, renderChosenTable } from './tables.js';

// Monotonic counter so restored + freshly-chosen entries keep a stable order.
let _orderSeq = 1;
function nextOrder() { return _orderSeq++; }

function busArray(kind) {
  const bus = TABLE_KINDS[kind].chosenBus;
  if (!Array.isArray(window[bus])) window[bus] = [];
  return window[bus];
}
function dataArray(kind) {
  return window[TABLE_KINDS[kind].dataBus] || [];
}
function recordFor(kind, id) {
  const idKey = TABLE_KINDS[kind].idKey;
  return dataArray(kind).find(c => c && (c[idKey] === id)) || null;
}

/** Build a chosen entry from a candidate record. */
function toEntry(kind, rec, id, order) {
  return {
    id_or_key: id,
    title: (rec && rec.title) || id,
    justification: (rec && (rec.description || rec.justification || rec.reason || rec.snippet)) || '',
    order: order != null ? order : nextOrder(),
    record: rec ? { ...rec } : { [TABLE_KINDS[kind].idKey]: id, title: id },
  };
}

/** Move all currently-ticked top-table rows into the chosen list (append, in DOM order). */
function chooseSelected(kind) {
  if (!S.currentKey) { alert('Load a case first.'); return; }
  const cfg = TABLE_KINDS[kind];
  const arr = busArray(kind);
  const have = new Set(arr.map(e => e.id_or_key));
  const boxes = document.querySelectorAll(`#${cfg.topEl} input.${cfg.topCheckbox}:checked`);
  if (!boxes.length) { alert('Tick one or more rows above first.'); return; }
  boxes.forEach(cb => {
    const id = cb.getAttribute(cfg.dataAttr) || cb.dataset.id || cb.dataset.key;
    if (!id || have.has(id)) return;
    have.add(id);
    arr.push(toEntry(kind, recordFor(kind, id), id));
  });
  renderStepTables(kind, dataArray(kind));
}

/** Append the given ids to the chosen list (used by LLM-suggest). Re-renders. */
export function chooseByIds(kind, ids) {
  const cfg = TABLE_KINDS[kind];
  const arr = busArray(kind);
  const have = new Set(arr.map(e => e.id_or_key));
  (ids || []).forEach(id => {
    if (!id || have.has(id)) return;
    have.add(id);
    arr.push(toEntry(kind, recordFor(kind, id), id));
  });
  renderStepTables(kind, dataArray(kind));
}

/** Move all currently-ticked chosen-table rows back out (they reappear up top). */
function clearSelected(kind) {
  const cfg = TABLE_KINDS[kind];
  const arr = busArray(kind);
  const boxes = document.querySelectorAll(`#${cfg.chosenEl} input.${cfg.chosenCheckbox}:checked`);
  if (!boxes.length) { alert('Tick one or more chosen rows first.'); return; }
  const remove = new Set();
  boxes.forEach(cb => remove.add(cb.getAttribute(cfg.dataAttr) || cb.dataset.id || cb.dataset.key));
  window[cfg.chosenBus] = arr.filter(e => !remove.has(e.id_or_key));
  renderStepTables(kind, dataArray(kind));
}

/**
 * Pre-populate the chosen list from a saved session's selections (on load).
 * Uses each selection's persisted `order` when present, else falls back to the
 * saved list order. Rebuilds `record` from the loaded candidate data when
 * available, else from the saved selection fields.
 */
export function restoreChosenFromSelections(kind, selections) {
  const cfg = TABLE_KINDS[kind];
  const sels = Array.isArray(selections) ? selections : [];
  const withOrder = sels.map((s, i) => ({ s, o: (s && typeof s.order === 'number') ? s.order : i }));
  withOrder.sort((a, b) => a.o - b.o);
  const arr = [];
  const maxOrder = withOrder.reduce((m, x) => Math.max(m, x.o), 0);
  withOrder.forEach(({ s, o }) => {
    const id = s.id_or_key || s.id || s.key;
    if (!id) return;
    const rec = recordFor(kind, id) || {
      [cfg.idKey]: id, title: s.title || id, description: s.justification || '',
      justification: s.justification || '', score: s.score,
    };
    arr.push(toEntry(kind, rec, id, o));
  });
  window[cfg.chosenBus] = arr;
  _orderSeq = Math.max(_orderSeq, maxOrder + 1);
  renderChosenTable(kind);
}

/** Current chosen selections for a step, as the confirm payload (with order). */
export function chosenSelections(kind) {
  return busArray(kind).map(e => ({
    id_or_key: e.id_or_key,
    title: e.title,
    justification: e.justification || '',
    order: e.order,
  }));
}

// Bound action wrappers (registry needs named, arg-less handlers).
function chooseTestLink() { chooseSelected('testlink'); }
function chooseZephyr() { chooseSelected('zephyr'); }
function chooseATP() { chooseSelected('atp'); }
function clearChosenTestLink() { clearSelected('testlink'); }
function clearChosenZephyr() { clearSelected('zephyr'); }
function clearChosenATP() { clearSelected('atp'); }

registerActions({
  chooseTestLink, chooseZephyr, chooseATP,
  clearChosenTestLink, clearChosenZephyr, clearChosenATP,
});
