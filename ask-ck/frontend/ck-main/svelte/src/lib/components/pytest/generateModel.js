// @ts-nocheck

// Pure logic for the Generate step (PtGenerate.svelte): data in, data out — no component
// state, no server calls, no DOM. Split out of PtGenerate so it can be unit-tested directly,
// the same split as zephyrModel.js / testComposerModel.js beside their components.

// --- Arrow-step ids -----------------------------------------------------------------------
// The two fixed arrow steps after the units. Unit ids come from the server ("setup", "tc1", …),
// so these are chosen never to collide with one.
export const GENERATE_SUMMARY_STEP_ID = "__generate_summary__";
export const GENERATE_REVIEW_STEP_ID = "__generate_review__";

// --- Units --------------------------------------------------------------------------------

/** A unit's title for messages, falling back to its id. */
export function unitTitle(units, unitId) {
  return units.find((u) => u.id === unitId)?.title ?? unitId;
}

// A unit's prompt travels with the request only when it is the reviewer's own: edited
// on this page, or an earlier kept edit the server handed back. Everything else is sent
// as a bare id and rendered fresh server-side — sending unedited text is how a stale tab
// once fed a whole run old prompts that the server then kept as edits (current/, 2026-09-07).
/** The dispatch body item for one unit, given that unit's generation state. */
export function dispatchItem(unitId, st) {
  const edited = st.storedEdit || st.prompt !== st.renderedPrompt;
  return edited && st.prompt.trim()
    ? { id: unitId, prompt: st.prompt, edited: true }
    : { id: unitId };
}

/** The status line once a generation run has settled, e.g. "3/4 units generated — 1 failed; …". */
export function settledSummary(units, generateState) {
  const total = units.length;
  const ok = units.filter((u) => generateState[u.id].code).length;
  const failed = units.filter((u) => generateState[u.id].error).length;
  return (
    `${ok}/${total} unit${total === 1 ? "" : "s"} generated` +
    (failed
      ? ` — ${failed} failed; re-run ${failed === 1 ? "it" : "them"} individually.`
      : ".")
  );
}

// --- Arrow-step statuses, counts and progress ----------------------------------------------

/**
 * Each unit's arrow-step status, keyed by unit id. First match wins:
 *   held fix waiting for Confirm Unit → "review"; high-severity finding → "error";
 *   confirmed → "covered"; has code → "review"; otherwise → "none".
 */
export function unitStatuses({ units, heldUnitIds, criticalUnitIds, confirmedIds, generateState }) {
  const next = {};
  for (const unit of units) {
    if (heldUnitIds.includes(unit.id)) {
      next[unit.id] = "review"; // a fix is waiting for its Confirm Unit
    } else if (criticalUnitIds.has(unit.id)) {
      next[unit.id] = "error";
    } else if (confirmedIds.includes(unit.id)) {
      next[unit.id] = "covered";
    } else if (generateState[unit.id]?.code) {
      next[unit.id] = "review";
    } else {
      next[unit.id] = "none";
    }
  }
  return next;
}

// Summary shows counts, not a per-unit list. 'error' (a high-severity review finding) is
// counted apart so the counts always add up to the number of units.
/** How many units are in each status: { covered, review, none, error }. */
export function countStatuses(statuses) {
  return Object.values(statuses).reduce(
    (acc, st) => ({ ...acc, [st]: (acc[st] || 0) + 1 }),
    { covered: 0, review: 0, none: 0, error: 0 },
  );
}

/** The Summary arrow step's status: "covered" once every unit is confirmed. */
export function summaryStatus(units, confirmedIds) {
  return units.length > 0 && units.every((u) => confirmedIds.includes(u.id))
    ? "covered"
    : "none";
}

/** Percent of units confirmed, for the progress bar. */
export function coveragePercent(units, statuses) {
  if (units.length === 0) return 0;
  const covered = Object.values(statuses).filter((s) => s === "covered").length;
  return Math.round((covered / units.length) * 100);
}

/** Where Confirm Unit goes next: the first unconfirmed unit, else the Summary step. */
export function nextAfterConfirm(units, confirmedIds) {
  const next = units.find((u) => !confirmedIds.includes(u.id));
  return next ? next.id : GENERATE_SUMMARY_STEP_ID;
}

// --- Which unit a finding or lint error is about -------------------------------------------
// A unit's arrow step turns red when the current (non-stale) review has a HIGH-severity
// finding about it. Which unit a finding is about COPIES the server's
// _unit_id_for_finding / _unit_id_for_text (routers/pytest_create.py) — keep the two in
// step if either changes. `where` is authoritative and resolved ALONE first (a `where` on
// TestSet can only ever mean setup), then `evidence`, then the finding's sequence `step`.
const TC_NAME_RX = /\bTestCase_(\d+)\b/;
const SETUP_REF_RX =
  /\bTestSet\b|\bconfigure\(\)|\btear_down\(\)|\bTestSet\.(configure|tear_down)\b/;
const LINE_REF_RX = /\bline (\d+)\b|:(\d+):/g;

// Each unit's 1-based line range in the assembled script, for "line N" references. The
// server reads these off the Python AST; this is an indentation-based approximation:
// a TestCase_N runs from its `class` line to the next top-level statement, and setup spans
// TestSet's configure()/tear_down() methods.
/** [{ id, lo, hi }] — each unit's line range in the assembled script. */
export function unitLineRanges(code) {
  const lines = (code || "").split("\n");
  const ranges = [];
  const isTopLevel = (l) => l.trim() !== "" && !/^\s/.test(l);
  const lastBefore = (i, lo) => {
    while (i > lo && lines[i - 1].trim() === "") i--;
    return i;
  };

  for (let i = 0; i < lines.length; i++) {
    const tc = /^class TestCase_(\d+)\b/.exec(lines[i]);
    if (tc) {
      let j = i + 1;
      while (j < lines.length && !isTopLevel(lines[j])) j++;
      ranges.push({ id: `tc${tc[1]}`, lo: i + 1, hi: lastBefore(j, i + 1) });
      continue;
    }
    if (/^class TestSet\b/.test(lines[i])) {
      let lo = null,
        hi = null;
      let j = i + 1;
      while (j < lines.length && !isTopLevel(lines[j])) {
        const m = /^(\s+)(async\s+)?def (configure|tear_down)\(/.exec(lines[j]);
        if (m) {
          const indent = m[1].length;
          let k = j + 1;
          while (
            k < lines.length &&
            (lines[k].trim() === "" || /^\s*/.exec(lines[k])[0].length > indent)
          )
            k++;
          lo = lo === null ? j + 1 : Math.min(lo, j + 1);
          hi = Math.max(hi ?? 0, lastBefore(k, j + 1));
          j = k;
          continue;
        }
        j++;
      }
      if (lo !== null) ranges.push({ id: "setup", lo, hi });
    }
  }
  return ranges;
}

/** The unit a piece of text names (TestCase_N, TestSet/configure/tear_down, or "line N"), or null. */
export function unitIdForText(text, ids, ranges) {
  text = text || "";
  const m = TC_NAME_RX.exec(text);
  if (m && ids.has(`tc${m[1]}`)) return `tc${m[1]}`;
  if (SETUP_REF_RX.test(text) && ids.has("setup")) return "setup";
  for (const lm of text.matchAll(LINE_REF_RX)) {
    const ln = Number(lm[1] || lm[2]);
    const hit = ranges.find((r) => r.lo <= ln && ln <= r.hi);
    if (hit) return hit.id;
  }
  return null;
}

/** The unit a review finding is about: its `where`, then `evidence`, then its sequence `step`. */
export function unitIdForFinding(f, units, ids, ranges) {
  const where = String(f.where || "");
  if (/\bTestSet\b/.test(where) && ids.has("setup")) return "setup";
  const fromWhere = unitIdForText(where, ids, ranges);
  if (fromWhere) return fromWhere;
  const fromEvidence = unitIdForText(String(f.evidence || ""), ids, ranges);
  if (fromEvidence) return fromEvidence;
  if (f.step == null) return null;
  // The unit whose sequence row is that step — step_prompts' source_n is the server's own
  // _unit_source_step(unit).n.
  return (
    units.find((u) => u.source_n != null && String(u.source_n) === String(f.step))?.id ?? null
  );
}

/** Units with a HIGH-severity finding in the current review — none while the review is stale. */
export function criticalUnitIds({ units, findings, code, stale }) {
  if (stale) return new Set(); // a stale review describes old code
  const ids = new Set(units.map((u) => u.id));
  const ranges = unitLineRanges(code);
  return new Set(
    findings
      .filter((f) => f.severity === "high")
      .map((f) => unitIdForFinding(f, units, ids, ranges))
      .filter(Boolean),
  );
}

// Units a lint error names — routed with the same rule as the red units (the server's
// _unit_id_for_text), which is also how the server sorts lint errors onto units. A lint
// error that names no unit is a whole-file problem: Fix Whole Script's job.
/** Units that a lint ERROR names. */
export function lintErrorUnitIds({ units, lintResults, code }) {
  const ids = new Set(units.map((u) => u.id));
  const ranges = unitLineRanges(code);
  return new Set(
    lintResults
      .filter((r) => r.level === "error")
      .map((r) => unitIdForText(r.message, ids, ranges))
      .filter(Boolean),
  );
}
