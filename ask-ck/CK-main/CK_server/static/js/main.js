// Entry point. Import order matters: session.js first so the fetch monkeypatch
// (X-CK-Session header) is installed before any other module can fire a request.
import './session.js';           // side-effect: session id + fetch patch
import './theme.js';             // side-effect: theme toggle
import './actions.js';           // side-effect: keydown + click dispatcher; exports registerActions
import { S } from './state.js';
import { initSidebarAccordion, goToPanel, updatePageHeader } from './nav.js';
import { initCases, onCaseSelectChange } from './cases.js';
import { updateAuthMethodUI, updateLLMStatus } from './llm.js';
import { ptManualSearch, ptFitEdited, ptProfileSelected } from './pytest.js';
// Tool modules imported for their side-effect registerActions() calls:
import './generator.js';
import './chosen.js';
import './db-search.js';
import './agent.js';

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

initSidebarAccordion();
initCases();
updateAuthMethodUI();
S.currentStep = 0;              // Generator defaults to step 0 when first opened
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
