// DB-search tools: merge + manual-search + LLM-suggest for TestLink/Zephyr/ATP.
//
// Merge only updates the candidate bus (window.current*) and re-renders both
// tables. BOTH search results and LLM suggestions land in the top ("candidates")
// table for the user to tick + Choose — nothing is promoted to the chosen list
// on the user's behalf, so accepting the LLM's picks is an explicit act of
// judgement about whether the search was any good. The `precheckIds` option
// still promotes straight to the chosen bus, but no caller uses it today. Row
// selection and confirm live in chosen.js.
import { registerActions } from './actions.js';
import { S } from './state.js';
import { renderStepTables } from './tables.js';
import { chooseByIds } from './chosen.js';
import { recordLLMDebug } from './llm-debug.js';
import { setButtonBusy, flashButtonDone } from './dom-helpers.js';
import { registerProvenance, renderProvenanceBlock } from './provenance.js';

// Mount a suggest panel's provenance block (transient — suggests persist nothing,
// so it renders empty and Refresh fills it live via dry_run).
function mountSuggestProvenance(mountId, panelId, endpoint) {
  const mount = document.getElementById(mountId);
  if (!mount || !S.currentKey) return;
  registerProvenance(panelId, () => endpoint + encodeURIComponent(S.currentKey), () => ({}));
  mount.innerHTML = renderProvenanceBlock(panelId);
}

/** Merge new ATP rows into window.currentATP by id (prefer higher score / richer reason).
 *  Exported for unit tests (js-tests/merge.spec.js); the app calls it internally. */
export function mergeATPCandidates(incoming, { precheckIds = null, source = 'search' } = {}) {
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
  renderStepTables('atp', merged);
  if (precheckIds && precheckIds.length) chooseByIds('atp', precheckIds);
}

export function mergeTestLinkCandidates(incoming, { precheckIds = null, source = 'search' } = {}) {
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
  renderStepTables('testlink', merged);
  if (precheckIds && precheckIds.length) chooseByIds('testlink', precheckIds);
}

export function mergeZephyrCandidates(incoming, { precheckIds = null, source = 'search' } = {}) {
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
  renderStepTables('zephyr', merged);
  if (precheckIds && precheckIds.length) chooseByIds('zephyr', precheckIds);
}

/** Comma-separated ids currently in a candidate pool, for keep_ids re-scoring. */
function poolIds(bus, idKey) {
  return (window[bus] || []).map(c => c && c[idKey]).filter(Boolean).join(',');
}

async function searchTestLink() {
  const qEl = document.getElementById('tlSearchQ');
  const q = (qEl && qEl.value || '').trim();
  if (!q) {
    alert('Enter TestLink search keywords first.');
    return;
  }
  try {
    const keep = poolIds('currentTestLink', 'id');
    const res = await fetch('/api/wizard/search_testlink?q=' + encodeURIComponent(q)
      + (keep ? '&keep_ids=' + encodeURIComponent(keep) : ''));
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
  if (!S.currentKey) {
    alert('Load a case first.');
    return;
  }
  const qEl = document.getElementById('tlSearchQ');
  const q = (qEl && qEl.value || '').trim();
  const btn = document.getElementById('tl-suggest-llm-btn');
  if (!setButtonBusy(btn, true, { label: 'Suggesting…' })) return;   // guard double-click
  let ok = false;
  try {
    const res = await fetch('/api/wizard/suggest_testlink/' + encodeURIComponent(S.currentKey), {
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
    mergeTestLinkCandidates(rows, { source: 'llm' });
    ok = true;
  } catch (e) {
    alert('Suggest TestLink with LLM failed: ' + e);
  } finally {
    setButtonBusy(btn, false);
    flashButtonDone(btn, ok);
    recordLLMDebug(btn);
    mountSuggestProvenance('tl-prov', 'panel-tl', '/api/wizard/suggest_testlink/');
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
    if (S.currentKey) url += '&case_key=' + encodeURIComponent(S.currentKey);
    const keep = poolIds('currentZephyr', 'key');
    if (keep) url += '&keep_ids=' + encodeURIComponent(keep);
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
  if (!S.currentKey) {
    alert('Load a case first.');
    return;
  }
  const qEl = document.getElementById('zephyrSearchQ');
  const q = (qEl && qEl.value || '').trim();
  const btn = document.getElementById('zp-suggest-llm-btn');
  if (!setButtonBusy(btn, true, { label: 'Suggesting…' })) return;   // guard double-click
  let ok = false;
  try {
    const res = await fetch('/api/wizard/suggest_zephyr/' + encodeURIComponent(S.currentKey), {
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
    mergeZephyrCandidates(rows, { source: 'llm' });
    ok = true;
  } catch (e) {
    alert('Suggest Zephyr with LLM failed: ' + e);
  } finally {
    setButtonBusy(btn, false);
    flashButtonDone(btn, ok);
    recordLLMDebug(btn);
    mountSuggestProvenance('zephyr-prov', 'panel-zephyr', '/api/wizard/suggest_zephyr/');
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
    const keep = poolIds('currentATP', 'id');
    const res = await fetch('/api/wizard/search_atp?q=' + encodeURIComponent(q)
      + (keep ? '&keep_ids=' + encodeURIComponent(keep) : ''));
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
  if (!S.currentKey) {
    alert('Load a case first.');
    return;
  }
  const qEl = document.getElementById('atpSearchQ');
  const q = (qEl && qEl.value || '').trim();
  const btn = document.getElementById('atp-suggest-llm-btn');
  if (!setButtonBusy(btn, true, { label: 'Suggesting…' })) return;   // guard double-click
  let ok = false;
  try {
    const res = await fetch('/api/wizard/suggest_atp/' + encodeURIComponent(S.currentKey), {
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
    mergeATPCandidates(rows, { source: 'llm' });
    ok = true;
  } catch (e) {
    alert('Suggest with LLM failed: ' + e);
  } finally {
    setButtonBusy(btn, false);
    flashButtonDone(btn, ok);
    recordLLMDebug(btn);
    mountSuggestProvenance('atp-prov', 'panel-atp', '/api/wizard/suggest_atp/');
  }
}


// Register this tool's data-action handlers.
registerActions({
  searchTestLink, suggestTestLinkWithLLM, searchZephyr,
  suggestZephyrWithLLM, searchATP, suggestATPWithLLM,
});
