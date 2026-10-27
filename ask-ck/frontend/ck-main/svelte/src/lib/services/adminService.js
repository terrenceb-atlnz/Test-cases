// @ts-nocheck

// COPIED OVER FROM current/admin/admin.js
// NOT PORTED (Svelte has no equivalent need):
//   - openAdminPanel()/goToPanel() — the Svelte reveal is local `isAdmin` state on
//     HomePage.svelte, not a router panel switch.
//   - registerActions({...}) — that's the vanilla data-action dispatch system;
//     Svelte binds on:click directly, so there is nothing to register into.

const ADMIN_API = "/api/admin";

export async function fetchAdminStatus() {
  try {
    const r = await fetch(`${ADMIN_API}/status`);
    return await r.json();
  } catch (e) {
    return { db: { ok: false, error: String(e) } };
  }
}

// MODIFIED FROM current/admin/admin.js TO WORK WITH SVELTE
// (refreshAdminStatus wrote straight into #admin-status' textContent; this returns the
// same string so the component can render it.)
export function describeAdminStatus(data) {
  const db = (data && data.db) || {};
  const c = db.counts || {};
  const vec = db.vector_search ? "on" : "off";
  const parts = Object.entries(c)
    .map(([k, v]) => `${k}:${v}`)
    .join(" · ");
  return (
    `DB ${db.ok ? "ready" : "NOT ready"} — ${parts || "no counts"} · vectors ${vec}` +
    (db.embeddings != null ? ` · ${db.embeddings} embeddings` : "")
  );
}

async function post(path, body) {
  const r = await fetch(ADMIN_API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.detail || "HTTP " + r.status);
  return d;
}

export async function resetWorkspaceLlmConfig() {
  return post("/reset-session", { scope: "workspace" });
}

export async function resetAllSessions() {
  return post("/reset-session", { scope: "all" });
}

export async function restartServer() {
  return post("/restart");
}

// --- R5 lint trends (PLAN-self-healing-generation.md §6.4) ---
// COPIED OVER FROM current/admin/admin.js (refreshLintTrends / renderLintTrendsCard).
// /lint_trends answers in three shapes: a normal aggregate, a thin one ({runs: 0}) and a
// failure ({error}). Read every field defensively. Read-only: the thresholds are server
// constants in routers/pytest_create.py.
export async function fetchLintTrends() {
  try {
    const r = await fetch("/api/pytest-create/lint_trends");
    if (r.ok) return await r.json();
    return { error: "HTTP " + r.status };
  } catch (e) {
    return { error: String(e) };
  }
}

// MODIFIED FROM current/admin/admin.js TO WORK WITH SVELTE
// (renderLintTrendsCard returned an HTML string + class name; this returns the pieces so the
// component renders them.) `note` is a single quiet line; otherwise `lines` are the numbers and
// `alarms` the crossed thresholds (empty = "no threshold crossed").
export function describeLintTrends(d) {
  if (!d) return { note: "Lint trends unavailable." };
  if (d.error) return { note: "Lint trends unavailable: " + String(d.error) };
  if (!d.runs) {
    return {
      note: "No assembly runs recorded yet — the trend starts at the first Assemble.",
    };
  }
  const byClass =
    Object.entries(d.by_class || {})
      .map(([k, v]) => `${k}:${v}`)
      .join(" · ") || "none";
  const rr =
    d.return_rate == null
      ? "n/a (no repairs attempted)"
      : Math.round(d.return_rate * 100) + "%";
  const head =
    `${d.runs} run(s)` +
    (d.window ? ` in a window of ${d.window}` : "") +
    (d.total_units != null ? ` · ${d.total_units} unit(s)` : "") +
    (d.prompt_version ? ` · prompt version ${d.prompt_version}` : "");
  return {
    lines: [
      head,
      `lint errors by class — ${byClass}`,
      `repair return rate — ${rr}`,
    ],
    alarms: (d.alarms || []).map((a) => a.detail || a.class || ""),
  };
}
