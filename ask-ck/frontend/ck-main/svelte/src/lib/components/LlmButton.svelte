<script>
// @ts-nocheck

// A button that triggers an LLM call, consistently, anywhere in the app: live progress
// text while busy, click-to-stop (true server-side cancel, not a client-only abort — see
// llmProgressService's own doc comment on why), and a token-usage badge on success. First
// extracted from CandidatePickerStep.svelte's Suggest-with-LLM button; every other
// LLM-triggering button (Objectives/Test Steps synthesis, Zephyr/ATP suggest) should use
// this instead of re-wiring the same five functions inline.
import Button from './Button.svelte';
import {
  startLlmProgress,
  cancelLlmCall,
  isCancelMessage,
  fetchLatestLlmUsage,
  fmtTokens,
} from '../services/llmProgressService.js';

/** @type {string} Idle button label, e.g. "Suggest with LLM" */
export let label = 'Run with LLM';

/** @type {string} Busy-state progress-ticker prefix, e.g. "Suggesting…" — a continuous verb,
    distinct from `label`'s imperative idle text (matches current/'s own llmButtonStart calls,
    which pass a different string here than the button's resting label). */
export let verb = 'Running…';

/** @type {(headers: Record<string, string>) => Promise<any>} The actual service call —
    `headers` carries X-CK-LLM-Call so the server can track/cancel this exact call. */
export let onRun = async () => null;

/** @type {((result: any) => void) | null} Called with the resolved value on success — the
    button has no idea whether that's candidates, an objective, or anything else; the caller
    decides what "success" means for its own domain. */
export let onResult = null;

/** @type {(() => Promise<boolean>) | null} Optional gate checked BEFORE the busy/progress
    state starts — e.g. Objectives' "no candidates chosen, continue anyway?" confirmation.
    Resolving false silently aborts (no error, no progress ticker ever shown); true proceeds
    exactly as if this prop weren't set. Runs before `isBusy` flips so a confirm dialog never
    races the progress ticker. */
export let onBeforeRun = null;

let isBusy = false;
let callId = null;
let progressLabel = label;
let error = '';
let usage = null;   // latest /api/llm/recent record — badge shown only on success

async function handleClick() {
  if (isBusy) {
    cancelLlmCall(callId);   // true server-side cancel — see llmProgressService
    return;
  }
  if (onBeforeRun) {
    const proceed = await onBeforeRun();
    if (!proceed) return;
  }
  isBusy = true;
  error = '';
  const progress = startLlmProgress(verb, ({ text }) => { progressLabel = text; });
  callId = progress.callId;
  try {
    const result = await onRun(progress.headers);
    usage = await fetchLatestLlmUsage();
    onResult && onResult(result);
  } catch (e) {
    const msg = (e && e.message) || String(e);
    if (!isCancelMessage(msg)) error = msg;
  } finally {
    progress.stop();
    isBusy = false;
    callId = null;
    progressLabel = label;
  }
}
</script>

<span class="llm-button-wrap">
  <Button
    variant="primary"
    sparkle={!isBusy}
    busy={isBusy}
    on:click={handleClick}
    title={isBusy ? 'Click to stop this LLM call — nothing will be kept' : ''}
  >{isBusy ? progressLabel : label}</Button>
  {#if usage && !usage.error}
    <span
      class="llm-token-badge"
      class:llm-token-badge-success={!!usage.usage}
      title={usage.usage?.cost_usd != null
        ? '$' + usage.usage.cost_usd
        : (usage.usage ? 'input tokens (prompt) / output tokens (generated)' : 'This transport does not report token usage')}
    >{fmtTokens(usage.usage)}</span>
  {/if}
</span>

{#if error}
  <p class="llm-button-error">{label} failed: {error}</p>
{/if}

<style>
  .llm-button-wrap {
    display: inline-flex;
    align-items: center;
    gap: 10px;
  }

  .llm-button-error {
    margin: 8px 0 0;
    color: var(--color-error);
    font-size: 0.88rem;
  }

  .llm-token-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    background: color-mix(in srgb, var(--color-text-muted) 18%, transparent);
    color: var(--color-text-muted);
  }

  .llm-token-badge-success {
    background: color-mix(in srgb, var(--color-success) 18%, transparent);
    color: var(--color-success);
  }
</style>
