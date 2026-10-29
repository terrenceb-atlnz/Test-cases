// @ts-nocheck

// PORTED FROM current/shared/version.js (the stale-tab guard), 2026-10-30, PLAN-svelte-cutover §2 #5.
//
// The server serves this app's committed dist/ straight off disk, so a new build ships with no
// restart — and a tab that is already open keeps running the OLD bundle indefinitely, with nothing
// to tell it so (three remote seats once sat on superseded code for a whole session). This records
// the server's build id at load, re-checks it, and reports when it moves. It never reloads on its
// own: the tabs hold unsaved work and live case locks, so the reload happens only when the user
// clicks (App.svelte shows a ConfirmModal).
//
// MODIFIED: the DOM overlay became a callback, so the component owns the prompt; `fetchImpl`
// and `pollMs` are injectable so the spec can drive it with fake timers.

const VERSION_API = "/api/version";
export const VERSION_POLL_MS = 60000;

/** The server's current build id, or "" when it cannot be read (offline, mid-restart). */
export async function fetchBuild(fetchImpl = fetch) {
  try {
    const r = await fetchImpl(VERSION_API, { cache: "no-store" });
    if (!r.ok) return "";
    const data = await r.json();
    return data.build || "";
  } catch (_) {
    return ""; // transient — say nothing, try again next tick
  }
}

/** Start watching. The first successful read sets the baseline (so a server unreachable at page
 *  load is still watched once it comes back); the first DIFFERENT read calls `onStale(build)` once
 *  and stops the watch. Returns a stop function for onDestroy. */
export function startVersionWatch(onStale, { pollMs = VERSION_POLL_MS, fetchImpl = fetch } = {}) {
  let baseline = "";
  let timer = null;
  let done = false;

  async function tick() {
    if (done) return;
    const build = await fetchBuild(fetchImpl);
    if (!build || done) return;
    if (!baseline) {
      baseline = build;
      return;
    }
    if (build !== baseline) {
      done = true;
      if (timer) clearInterval(timer);
      timer = null;
      onStale(build);
    }
  }

  timer = setInterval(tick, pollMs);
  tick();
  return function stop() {
    done = true;
    if (timer) clearInterval(timer);
    timer = null;
  };
}
