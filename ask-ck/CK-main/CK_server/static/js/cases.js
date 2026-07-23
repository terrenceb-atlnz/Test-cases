// Case-select plumbing shared by the Generator and PyTest Creator.
import { S } from './state.js';
import { updatePageHeader } from './nav.js';

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

export function syncHiddenCaseSel(key) {
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

export function onCaseSelectChange(sourceSel) {
  const openSel = document.getElementById('caseSelOpen');
  const doneSel = document.getElementById('caseSelDone');
  handleCasePairChange(openSel, doneSel, sourceSel, (key, title) => {
    S.currentKey = key;
    window.currentCaseTitle = title;
    syncHiddenCaseSel(key);
    updatePageHeader();
  });
}

function onPtCaseSelectChange(sourceSel) {
  // PyTest Creator: two dropdowns (Open/Partial + Complete), mutually exclusive like
  // the Generator's pair. Must never touch S.currentKey / #caseSel / the page header —
  // those belong to the Generator's loaded case.
  const openSel = document.getElementById('ptCaseSelOpen');
  const doneSel = document.getElementById('ptCaseSelDone');
  handleCasePairChange(openSel, doneSel, sourceSel, (key, title) => {
    S.ptCase = { key: key, title: title };
    const s = document.getElementById('pt-selected-summary');
    if (s) s.textContent = key ? `Selected: ${key}` : '';
  });
}

export function getActiveCaseKey() {
  const openSel = document.getElementById('caseSelOpen');
  const doneSel = document.getElementById('caseSelDone');
  const hidden = document.getElementById('caseSel');
  if (openSel && openSel.value) return openSel.value;
  if (doneSel && doneSel.value) return doneSel.value;
  if (hidden && hidden.value) return hidden.value;
  return S.currentKey || null;
}

let _caseSelectListenersBound = false;

// PyTest Creator's two dropdowns have their OWN data source: /api/pytest-create/pt_cases
// splits the Generator-Complete cases by PyTest work state (Open/Partial vs Complete),
// which the wizard's /cases endpoint doesn't know about. Independent of the Generator's
// selection — never touches S.currentKey / the page header.
export async function refreshPtCaseSelects() {
  const openSel = document.getElementById('ptCaseSelOpen');
  const doneSel = document.getElementById('ptCaseSelDone');
  if (!openSel && !doneSel) return;
  try {
    const res = await fetch('/api/pytest-create/pt_cases');
    if (!res.ok) return;
    const d = await res.json();
    const counts = d.counts || {};
    const openLabel = document.getElementById('ptCaseSelOpenLabel');
    const doneLabel = document.getElementById('ptCaseSelDoneLabel');
    if (openLabel) {
      const n = counts.in_progress != null ? counts.in_progress : '—';
      const p = counts.partials != null ? counts.partials : 0;
      openLabel.innerHTML = `Open/Partial <span class="case-count">(${n}${p ? `; ${p} in progress` : ''})</span>`;
    }
    if (doneLabel) doneLabel.innerHTML = `Complete <span class="case-count">(${counts.complete != null ? counts.complete : '—'})</span>`;

    fillCaseSelect(openSel, (d.in_progress && d.in_progress.grouped) || [], 'Select open or partial case…');
    fillCaseSelect(doneSel, (d.complete && d.complete.grouped) || [], 'Select completed case…');

    // Restore the current PyTest selection into whichever dropdown now holds it.
    const keep = S.ptCase.key;
    if (keep) {
      const inOpen = openSel && Array.from(openSel.options).some(o => o.value === keep);
      const inDone = doneSel && Array.from(doneSel.options).some(o => o.value === keep);
      if (inDone) { doneSel.value = keep; if (openSel) openSel.value = ''; }
      else if (inOpen) { openSel.value = keep; if (doneSel) doneSel.value = ''; }
      else {
        S.ptCase = { key: null, title: null };
        const s = document.getElementById('pt-selected-summary');
        if (s) s.textContent = '';
      }
    }
  } catch (e) {
    /* offline — leave placeholders */
  }
}

// Dynamic case lists: open/partial vs complete (from refined-cases + sessions)
export async function refreshCaseSelects(preserveKey) {
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
  // Keep the PyTest Creator dropdowns in sync on every general refresh.
  await refreshPtCaseSelects();
}

export async function initCases() {
  const openSel = document.getElementById('caseSelOpen');
  const doneSel = document.getElementById('caseSelDone');
  const ptOpenSel = document.getElementById('ptCaseSelOpen');
  const ptDoneSel = document.getElementById('ptCaseSelDone');
  if (!_caseSelectListenersBound) {
    if (openSel) openSel.addEventListener('change', () => onCaseSelectChange(openSel));
    if (doneSel) doneSel.addEventListener('change', () => onCaseSelectChange(doneSel));
    if (ptOpenSel) ptOpenSel.addEventListener('change', () => onPtCaseSelectChange(ptOpenSel));
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
