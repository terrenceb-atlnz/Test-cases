// Sidebar accordion + panel/step navigation.
import { registerActions } from './actions.js';
import { S } from './state.js';
import { renderLlmDebugFooter } from './llm-debug.js';
import { loadStepCandidates, renderObjectiveResult, renderReviewSummary, renderStepsResult, synthesize } from './generator.js';
import { ptSession, renderPtFragPanel, renderPtGenPanel, renderPtRunPanel, renderPtSearchPanel, renderPtSeqPanel, renderPtTestboxPanel, renderPtValidatePanel } from './pytest.js';

export function initSidebarAccordion() {
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
export function goToPanel(panelId) {
  S.currentPanel = panelId;
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

  // Session debug JSON is the Generator's S.currentSession — only meaningful on the
  // Objective/Test Case Generator step panels (step-0..step-5), not other tools/Main.
  const dbg = document.getElementById('session-debug');
  if (dbg) dbg.classList.toggle('hidden', !/^step-\d+$/.test(panelId));

  // LLM debug footer is per-panel: show this panel's last LLM request (or hide).
  renderLlmDebugFooter();

  const ptRenderers = {
    'panel-pt-seq': renderPtSeqPanel,
    'panel-pt-search': renderPtSearchPanel,
    'panel-pt-frag': renderPtFragPanel,
    'panel-pt-gen': renderPtGenPanel,
    'panel-pt-run': renderPtRunPanel,
    'panel-pt-validate': renderPtValidatePanel,
    'panel-pt-testbox': renderPtTestboxPanel,
  };
  if (ptRenderers[panelId]) ptRenderers[panelId]();
}

export function goToStep(step) {
  // Generator navigation. The numeric step scheme (data-step / step-N ids /
  // session keys step1..step5 / confirm_step 1-3) is load-bearing — sidebar
  // labels renumbered 1-6 are display-only and do NOT shift these values.
  S.currentStep = step;
  goToPanel('step-' + step);

  // Steps 1-3 fetch their own candidate pool on first visit (see
  // generator.loadStepCandidates): none of it is loaded at case-load time, and all
  // three behave identically. Deliberately not awaited — navigation must stay
  // instant; the table fills in when the fetch lands.
  if (step >= 1 && step <= 3) {
    loadStepCandidates(step);
  }
  if (step === 4) {
    renderReviewSummary();
    renderObjectiveResult();
  }
  if (step === 5) {
    renderStepsResult();
  }
}

export function updatePageHeader() {
  const titleEl = document.querySelector('.page-title');
  const descEl = document.querySelector('.page-description');
  if (!titleEl || !descEl) return;

  // The Main splash carries its own hero header; hide the page header there.
  const headerEl = document.querySelector('.page-header');
  if (headerEl) headerEl.classList.toggle('hidden', S.currentPanel === 'panel-main');

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
    'panel-pt-frag': { title: 'PyTest Creator', desc: 'Step 4: gather reusable code fragments, then confirm.' },
    'panel-pt-gen': { title: 'PyTest Creator', desc: 'Step 5: fill the skeleton template, name, lint and save the script, then confirm.' },
    'panel-pt-run': { title: 'PyTest Creator', desc: 'Step 6: execute on a stored testbox and review the parsed log.' },
    'panel-pt-validate': { title: 'PyTest Creator', desc: 'Step 7: final validation loop — fix with LLM until all cases PASS.' },
    'panel-pt-testbox': { title: 'PyTest Creator', desc: 'Manage stored testbox connections for the Run step.' }
  };

  const eyebrowEl = document.querySelector('.page-eyebrow');
  const meta = PANEL_META[S.currentPanel] || {};
  if (meta.title) {
    if (eyebrowEl) eyebrowEl.textContent = '';
    titleEl.textContent = meta.title;
    descEl.textContent = meta.desc || '';
    return;
  }
  // Generator panels (step-N): static tool eyebrow above the dynamic case title.
  if (eyebrowEl) eyebrowEl.textContent = 'Objective / Test Case Generator';
  if (S.currentKey) {
    const t = window.currentCaseTitle || '';
    titleEl.textContent = t ? `${S.currentKey} — ${t}` : S.currentKey;
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


// Register this tool's data-action handlers.
registerActions({
  goToPanel, goToStep,
});
