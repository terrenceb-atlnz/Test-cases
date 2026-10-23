<script>
  // @ts-nocheck

  import StatusBadge from "../StatusBadge.svelte";
  import CodeEditor from "../CodeEditor.svelte";
  import chevronIcon from "../../../assets/icons/chevron-right.svg";

  // The holistic review's findings (ported from current/'s ptRenderReview). A review returns
  // FINDINGS, never a rewrite — a finding becomes a change only through a fix.

  // --- Props: data --------------------------------------------------------------------
  /** @type {{ at: string, findings: Array<{ severity: string, where?: string, step?: string|number,
      kind?: string, what?: string, evidence?: string, suggestion?: string }> } | null}
      The review to show — nothing renders until it has an `at`. */
  export let review = null;

  /** @type {boolean} The code has changed since this review (the server's gen_state.review_stale)
      — the findings are then shown collapsed, each saying whether its evidence is still there. */
  export let stale = false;

  /** @type {string} The script as it is now — what a stale finding's evidence is checked against. */
  export let code = "";

  // --- Derived ------------------------------------------------------------------------
  $: findings = review?.findings || [];
  $: counts = ["high", "medium", "low"]
    .map((sv) => ({ sv, n: findings.filter((f) => f.severity === sv).length }))
    .filter((c) => c.n)
    .map((c) => `${c.n} ${c.sv}`)
    .join(" · ");

  // Each severity shows as the status icon of the same colour used across the app: high = the
  // red Critical icon, medium = the amber In Review icon, low = the grey Not started icon.
  const SEV_STATUS = { high: "error", medium: "review", low: "none" };

  // Presence check ignores ALL whitespace, so re-indenting doesn't read as "gone".
  function normWs(t) {
    return String(t || "").replace(/\s+/g, "");
  }
  function evidencePresent(text, evidence) {
    const ev = normWs(evidence);
    if (!ev) return null;
    return normWs(text).includes(ev);
  }
</script>

{#if review?.at}
  <div class="review-result">
    {#if findings.length === 0}
      <p class="review-head">
        <span class="review-badge review-badge-success"
          >Review: No findings</span
        >
      </p>
      <p class="review-note">
        Reviewed {review.at} — nothing found beyond the static checks.
      </p>
    {:else if stale}
      <div>
        <div class="review-note">
          {findings.length} stale finding(s) — {counts}
        </div>
        {@render findingsList()}
      </div>
    {:else}
      <p class="review-head">
        <span class="review-badge">Review: {findings.length} finding(s)</span>
        <span class="review-note">{counts}</span>
      </p>
      {@render findingsList()}
    {/if}
  </div>
{/if}
{#if !review?.at}
  <div>
    <p class="review-note">
      Review with LLM to produce a holistic review of each error in the
      assembled script.
    </p>
  </div>
{/if}

{#snippet findingsList()}
  <div class="review-findings">
    {#each findings as f}
      {@const present = stale ? evidencePresent(code, f.evidence) : null}

      <div
        class="review-finding review-{f.severity}"
        class:review-gone={present === false}
      >
        <details>
          <summary class="finding-head">
            <img
              class="finding-chevron"
              src={chevronIcon}
              alt=""
              aria-hidden="true"
            />
            <StatusBadge status={SEV_STATUS[f.severity] || "none"} />
            <b>{f.where || "(script)"}</b>
            {#if f.step}<span class="review-note">step {f.step}</span>{/if}
            <span class="review-note">{f.kind}</span>
            {#if stale && f.evidence}
              {#if present}
                <span
                  class="review-badge review-badge-medium"
                  title="The quoted lines are still in the current script"
                  >Evidence still present</span
                >
              {:else}
                <span
                  class="review-badge review-badge-success"
                  title="The quoted lines are no longer in the current script"
                  >Evidence gone</span
                >
              {/if}
            {/if}
          </summary>
          <div>{f.what}</div>
          {@render findingsDetails(f.evidence, f.suggestion)}
        </details>
      </div>
    {/each}
  </div>
{/snippet}

{#snippet findingsDetails(evidence, suggestion)}
  {#if evidence}
    <div class="review-evidence">
      <CodeEditor value={evidence} readonly height="auto" maxHeight="240px" />
    </div>
  {/if}
  {#if suggestion}<div class="review-note">suggested: {suggestion}</div>{/if}
{/snippet}

<style>
  .review-result {
    margin: 0 0 24px;
  }

  .review-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin: 16px 0 8px;
  }

  .review-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    background: color-mix(in srgb, var(--color-text-muted) 18%, transparent);
    color: var(--color-text);
  }

  .review-badge-success {
    background: color-mix(in srgb, var(--color-success) 18%, transparent);
    color: var(--color-success);
  }

  .review-badge-medium {
    background: color-mix(in srgb, var(--color-warning) 18%, transparent);
    color: var(--color-warning);
  }

  .review-note {
    margin: 0;
    color: var(--color-text-muted);
    font-size: 0.85rem;
  }

  .finding-chevron {
    flex: 0 0 auto;
    width: 16px;
    height: 16px;
    filter: var(--filter-status-none);
    transition: transform 0.15s ease;
  }

  details[open] > summary .finding-chevron {
    transform: rotate(90deg);
  }
  summary.finding-head {
    list-style: none;
    cursor: pointer;
  }

  summary.finding-head::-webkit-details-marker {
    display: none;
  }

  .finding-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }

  .review-findings {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 8px;
    overflow: scroll;
    max-height: 55vh;
    padding: 12px;
    border-top: 5px solid var(--color-border-surface);
    border-bottom: 5px solid var(--color-border-surface);
  }

  .review-finding {
    padding: 10px 12px;
    border: 2px solid var(--color-text-muted);
    border-radius: 5px;
    background: var(--color-bg-surface);
    font-size: 0.9rem;
    overflow-wrap: anywhere;
  }

  .review-high {
    border-color: var(--color-error);
  }

  .review-medium {
    border-color: var(--color-warning);
  }

  .review-gone {
    opacity: 0.35;
  }

  .review-evidence {
    margin: 8px 0;
  }
</style>
