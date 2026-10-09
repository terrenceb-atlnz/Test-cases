<script>
  // A button with the same busy / done / error states as shared/dom-helpers.js setButtonBusy +
  // flashButtonDone, rendered by Svelte (those helpers rewrite innerHTML, which would fight
  // Svelte for the element). Same classes, so the existing CSS on both UIs styles it.
  let { id = undefined, cls = 'btn btn-primary', label, busyLabel = 'Working…', busy = false,
        flash = null, disabled = false, title = undefined, onclick } = $props();
</script>

<button {id} type="button" class={cls} class:is-busy={busy} class:is-done={flash === 'done'}
  class:is-error={flash === 'error'} aria-busy={busy ? 'true' : undefined}
  disabled={busy || disabled} {title} {onclick}>
  {#if busy}<span class="ck-spinner" aria-hidden="true"></span><span class="ck-busy-label">{busyLabel}</span>{:else}{label}{/if}
</button>
