<script>
// @ts-nocheck

  import { onMount, onDestroy } from 'svelte';
  import { EditorState, Compartment } from '@codemirror/state';
  import { EditorView, placeholder as placeholderExt } from '@codemirror/view';
  import { basicSetup } from 'codemirror';
  import { syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language';
  import { python } from '@codemirror/lang-python';
  import { vscodeDark, vscodeLight } from '@uiw/codemirror-theme-vscode';
  import { resolvedTheme } from '../theme.js';

  /** @type {string} Bindable document text */
  export let value = '';

  /** @type {boolean} */
  export let readonly = false;

  /** @type {string} */
  export let placeholder = '';

  /** @type {string} CSS height for the editor box, e.g. '260px' */
  export let height = '260px';

  /** @type {'python' | 'none'} */
  export let language = 'python';

  let container;
  let view;
  const highlightCompartment = new Compartment();

  // Applied once at creation — background/border/font follow the app's own design tokens via
  // var(...), so they already track the light/dark toggle without needing to be reconfigured.
  const baseTheme = EditorView.theme({
    '&': {
      height,
      fontSize: '12px',
      border: '1px solid var(--color-border-surface)',
      borderRadius: '10px',
      overflow: 'hidden'          // keeps VS Code's background inside the rounded corners
    },
    '.cm-content': {
      fontFamily: "Consolas, 'Courier New', monospace",   // VS Code's default font
      padding: '10px 0'
    },
    '.cm-scroller': {
      overflow: 'auto'
    },
    '.cm-gutters': {
      border: 'none'
    },
    '&.cm-focused': {
      outline: 'none'
    }
  });


  function highlightExtensionFor(themeName) {
    return themeName === 'dark' ? vscodeDark : vscodeLight;
  }

  onMount(() => {
    view = new EditorView({
      parent: container,
      state: EditorState.create({
        doc: value,
        extensions: [
          basicSetup,
          ...(language === 'python' ? [python()] : []),
          EditorView.lineWrapping,
          baseTheme,
          highlightCompartment.of(highlightExtensionFor($resolvedTheme)),
          ...(placeholder ? [placeholderExt(placeholder)] : []),
          EditorState.readOnly.of(readonly),
          EditorView.editable.of(!readonly),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              value = update.state.doc.toString();
            }
          })
        ]
      })
    });
  });

  onDestroy(() => {
    view?.destroy();
  });

  // Push external value changes (e.g. switching to a different unit/step) into the editor —
  // guarded so edits originating from the editor itself (which already set `value` above) don't
  // trigger a redundant re-dispatch.
  $: if (view && value !== view.state.doc.toString()) {
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: value ?? '' }
    });
  }

  $: if (view) {
    view.dispatch({ effects: highlightCompartment.reconfigure(highlightExtensionFor($resolvedTheme)) });
  }
</script>

<div class="code-editor" bind:this={container}></div>

<style>
  .code-editor {
    border: 1px solid var(--color-accent);
    border-radius: 10px;
  } 
</style>