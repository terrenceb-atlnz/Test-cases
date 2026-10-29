/** Per-seat remembered setup answers (a convenience — confirmed every launch). */
//@ts-nocheck
const SETUP_KEY = "ck.tc.setup";
export function loadSetup(store) {
  try {
    return JSON.parse(
      (store || window.localStorage).getItem(SETUP_KEY) || "{}",
    );
  } catch (_) {
    return {};
  }
}
export function saveSetup(v, store) {
  try {
    (store || window.localStorage).setItem(SETUP_KEY, JSON.stringify(v));
  } catch (_) {
    /* private mode */
  }
}

/** "u0=1, u1=7" → {u0: 1, u1: 7}; ignores anything else. */
export function parseOutlets(text) {
  const out = {};
  for (const part of String(text || "").split(/[,\s]+/)) {
    const m = part.match(/^(u\d{1,2})=(\d{1,3})$/);
    if (m) out[m[1]] = Number(m[2]);
  }
  return out;
}

export function formatOutlets(o) {
  return Object.entries(o || {})
    .map(([k, v]) => `${k}=${v}`)
    .join(", ");
}

/** The request body for POST /runs from the setup fields. */
export function runBody(kind, setup, extra = {}) {
  const pdu = setup.pduIp
    ? { ip: setup.pduIp.trim(), outlets: parseOutlets(setup.outlets) }
    : null;
  return Object.assign(
    {
      kind,
      testbox: (setup.testbox || "").trim(),
      consoles: (setup.consoles || "").trim(),
      pdu,
      constraints: (setup.constraints || "").trim(),
      options: { email: (setup.email || "").trim() || null },
    },
    extra,
  );
}

/** Run Scripts' share link (PLAN-run-scripts §3): the scripts in run order and the bench settings,
 *  never the email (R-D4) — whoever opens it gets the mail. Parsed by test-composer.js deepLink. */
export function scriptsLink(href, { source, scripts, setup, start }) {
  const u = new URL(href);
  u.search = "";
  u.hash = "";
  const put = (k, v) => {
    const t = String(v || "").trim();
    if (t) u.searchParams.set(k, t);
  };
  put("panel", "run-scripts");
  put("source", source);
  put("scripts", (scripts || []).join(","));
  put("testbox", setup.testbox);
  put("consoles", setup.consoles);
  put("pdu", setup.pduIp);
  put("outlets", setup.outlets);
  put("constraints", setup.constraints);
  put("start", start);
  return u.toString();
}

export const VERDICT_ORDER = [
  "PASS",
  "FAIL",
  "PARTIAL",
  "UNSUPPORTED",
  "ERROR",
  "BLOCKED",
  "NOT TESTED",
  "SKIP",
  "PENDING",
];

/** The results table grouped by test cycle, in first-seen order; cases without a cycle last. */
export function byCycle(table) {
  const groups = new Map();
  for (const row of table || []) {
    const k = row.cycle || "";
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(row);
  }
  const keys = [...groups.keys()].sort((a, b) => (a === "") - (b === ""));
  return keys.map((k) => ({ cycle: k || null, rows: groups.get(k) }));
}

export function effectiveVerdict(row) {
  return (row.regrade && row.regrade.verdict) || row.verdict;
}

export function verdictCounts(table) {
  const c = {};
  for (const r of table || []) {
    const v = effectiveVerdict(r);
    c[v] = (c[v] || 0) + 1;
  }
  return VERDICT_ORDER.filter((v) => c[v])
    .map((v) => ({ verdict: v, n: c[v] }))
    .concat(
      Object.keys(c)
        .filter((v) => !VERDICT_ORDER.includes(v))
        .map((v) => ({ verdict: v, n: c[v] })),
    );
}

export function fmtDuration(ms) {
  if (ms == null || ms < 0) return "—";
  const s = Math.round(ms / 1000);
  const h = Math.floor(s / 3600),
    m = Math.floor((s % 3600) / 60),
    x = s % 60;
  return h
    ? `${h}h ${String(m).padStart(2, "0")}m`
    : m
      ? `${m}m ${String(x).padStart(2, "0")}s`
      : `${x}s`;
}

export function fmtTokens(n) {
  if (n == null) return "—";
  return n >= 1e6
    ? `${(n / 1e6).toFixed(2)}M`
    : n >= 1e3
      ? `${(n / 1e3).toFixed(1)}k`
      : String(n);
}

/** Tokens in a result event's model_usage (all models, subagents included). */
export function tokensOf(modelUsage) {
  let t = 0;
  for (const u of Object.values(modelUsage || {})) {
    t += [
      "inputTokens",
      "outputTokens",
      "cacheReadInputTokens",
      "cacheCreationInputTokens",
    ].reduce((a, k) => a + (u[k] || 0), 0);
  }
  return t || null;
}
