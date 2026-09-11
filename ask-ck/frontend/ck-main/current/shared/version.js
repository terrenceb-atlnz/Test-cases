// Stale-tab guard.
//
// Static assets are served straight off disk, so shipping a frontend change
// needs no server restart — which also means a tab that is already open keeps
// running the OLD modules indefinitely, with nothing to tell it so. Three
// remote seats sat on superseded code for a whole session before anyone
// noticed. This records the build id at load, re-checks it, and asks the user
// to refresh when it moves.
//
// It never reloads on its own. The wizard holds unsaved selections and live
// case locks, and throwing away someone's in-progress work to apply a UI change
// is a bad trade — the reload happens only when they click.
const POLL_MS = 60000;

let baseline = '';
let timer = null;
let shown = false;

async function fetchBuild() {
  try {
    const res = await fetch('/api/version', { cache: 'no-store' });
    if (!res.ok) return '';
    const data = await res.json();
    return data.build || '';
  } catch (_) {
    return '';   // offline or mid-restart: say nothing, try again next tick
  }
}

function showUpdatePanel() {
  if (shown) return;                                  // one prompt per tab
  shown = true;
  if (timer) { clearInterval(timer); timer = null; }  // nothing left to watch for

  const overlay = document.createElement('div');
  overlay.className = 'update-overlay';
  overlay.innerHTML = `
    <div class="update-dialog" role="alertdialog" aria-modal="true"
         aria-labelledby="ck-update-title" aria-describedby="ck-update-body">
      <div class="update-title" id="ck-update-title">Server updated</div>
      <div class="update-body" id="ck-update-body">
        This page is running an older version of Ask CK. Refresh to load the
        current one. Anything you have not saved will be lost.
      </div>
      <button type="button" class="btn btn-primary" id="ck-update-ok">OK, refresh</button>
    </div>`;
  document.body.appendChild(overlay);

  const btn = overlay.querySelector('#ck-update-ok');
  btn.addEventListener('click', () => window.location.reload());
  btn.focus();
}

async function tick() {
  const build = await fetchBuild();
  if (!build) return;                       // transient failure — ignore it
  if (!baseline) { baseline = build; return; }   // first success sets the baseline
  if (build !== baseline) showUpdatePanel();
}

// Poll on a timer, and take a baseline immediately. Establishing the baseline
// inside tick() rather than here means a server that is briefly unreachable at
// page load still gets watched once it comes back.
timer = setInterval(tick, POLL_MS);
tick();
