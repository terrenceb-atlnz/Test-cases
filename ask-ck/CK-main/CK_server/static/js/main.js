// Entry point. Import order matters: session.js first so the fetch monkeypatch
// (X-CK-Session header) is installed before any other module can fire a request.
import './session.js';           // side-effect: session id + fetch patch
import './theme.js';             // side-effect: theme toggle
import './actions.js';           // side-effect: keydown + click dispatcher; exports registerActions
import { S } from './state.js';
import { initSidebarAccordion, goToPanel, updatePageHeader } from './nav.js';
import { initCases, onCaseSelectChange } from './cases.js';
import { updateAuthMethodUI, updateLLMStatus, loadWorkspaceLLMConfig, applyLocalLlmMode, applyClaudeMode } from './llm.js';
import { ptProfileSelected, ptLoadCase } from './pytest.js';
import { readSnapshot, waitForOptions, hasOption } from './session-restore.js';
import { onPtCaseSelectChange } from './cases.js';
import { openAdminPanel } from './admin.js';
// Tool modules imported for their side-effect registerActions() calls:
import './provenance.js';        // side-effect: provRefresh/provCopy* actions (shared)
import './generator.js';
import './chosen.js';
import './db-search.js';
import './agent.js';
import './version.js';    // side-effect: stale-tab guard (polls /api/version)

// Fetch a stub tool router's /status message into a placeholder status element.
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

// Read the pre-refresh snapshot FIRST. goToPanel() records wherever it moves to,
// so the boot default ('panel-main', below) overwrites the stored panel before an
// async restore could read it — the restore then faithfully returned to
// 'panel-main' every time.
const BOOT_SNAPSHOT = readSnapshot();

initSidebarAccordion();
initCases();
updateAuthMethodUI();
S.currentStep = 0;              // Generator defaults to step 0 when first opened
goToPanel('panel-main');     // Landing view = Main splash / Help home
updateLLMStatus();
loadWorkspaceLLMConfig();       // cold-load: reflect the persisted login (incl. Local LLM key state)
loadToolStatus('zephyr-tool', 'zt-info-status');
loadToolStatus('test-composer', 'tc-status');

// Restore where the user was before a refresh, then fall back to the old
// default (first open/partial case) only when there is nothing to restore.
// This waits on the case lists rather than firing on a fixed timeout — the old
// 200ms guess raced initCases()' fetch on a cold load.
async function restoreUiState() {
  const snap = BOOT_SNAPSHOT;

  // --- Generator: selecting IS loading, so the dropdown is the whole state ---
  const genSel = await waitForOptions('caseSelOpen');
  if (snap.genKey && (hasOption('caseSelOpen', snap.genKey) || hasOption('caseSelDone', snap.genKey))) {
    const which = hasOption('caseSelOpen', snap.genKey) ? 'caseSelOpen' : 'caseSelDone';
    const sel = document.getElementById(which);
    sel.value = snap.genKey;
    onCaseSelectChange(sel);
  } else if (genSel && !genSel.value && !snap.genKey) {
    // Unchanged pre-existing default: prefer the first open/partial case.
    for (let i = 0; i < genSel.options.length; i++) {
      if (genSel.options[i].value) { genSel.selectedIndex = i; onCaseSelectChange(genSel); break; }
    }
  }

  // --- PyTest Creator: selection and load are separate, so re-load only a case
  // that was actually loaded. This re-acquires its lock, exactly as the user's
  // own click did before the refresh.
  let ptRestored = false;
  if (snap.ptKey) {
    await waitForOptions('ptCaseSelOpen');
    const which = hasOption('ptCaseSelOpen', snap.ptKey) ? 'ptCaseSelOpen'
                : hasOption('ptCaseSelDone', snap.ptKey) ? 'ptCaseSelDone' : null;
    if (which) {
      const sel = document.getElementById(which);
      sel.value = snap.ptKey;
      onPtCaseSelectChange(sel);
      if (snap.ptLoaded) { await ptLoadCase(); ptRestored = true; }
    }
  }

  // --- Panel last: ptLoadCase() navigates to 2. Sequence on success, which
  // would otherwise overwrite the panel the user was actually on.
  const panel = snap.panel;
  if (panel && document.getElementById(panel)) {
    const isPt = panel.startsWith('panel-pt-');
    // Don't drop the user into a PyTest panel whose case failed to come back.
    if (!isPt || ptRestored || panel === 'panel-pt-cases' || panel === 'panel-pt-testbox') {
      goToPanel(panel);
    } else {
      goToPanel('panel-pt-cases');
    }
  }
  updatePageHeader();
}
restoreUiState();

// Form-control bindings that were previously inline onchange/onkeydown attributes.
document.querySelectorAll('input[name="llmAuthMethod"]').forEach((radio) => {
  radio.addEventListener('change', updateAuthMethodUI);
});
// Live Fast/Thinking toggle — persists the mode immediately (no Apply click).
document.querySelectorAll('input[name="localLlmMode"]').forEach((radio) => {
  radio.addEventListener('change', applyLocalLlmMode);
});
// Live Haiku/Sonnet/Opus toggle for the local Claude agent — persists immediately.
document.querySelectorAll('input[name="claudeMode"]').forEach((radio) => {
  radio.addEventListener('change', applyClaudeMode);
});
// Double-click CK's face → hidden Admin panel (single-click still goes Home,
// via the logo's data-action="goToPanel"). dblclick fires after the click, so
// the two don't conflict — you land Home for a beat, then Admin opens.
{
  const logo = document.querySelector('.sidebar-logo');
  if (logo) logo.addEventListener('dblclick', (e) => { e.preventDefault(); openAdminPanel(); });
}
{
  const prof = document.getElementById('pt-run-profile');
  if (prof) prof.addEventListener('change', function () { ptProfileSelected(this); });
}
