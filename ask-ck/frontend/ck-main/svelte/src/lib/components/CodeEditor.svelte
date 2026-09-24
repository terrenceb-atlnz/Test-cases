<script>
  import { onMount, onDestroy } from 'svelte';
  import { EditorState, Compartment } from '@codemirror/state';
  import { EditorView, placeholder as placeholderExt } from '@codemirror/view';
  import { basicSetup } from 'codemirror';
  import { syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language';
  import { python } from '@codemirror/lang-python';
  import { oneDarkHighlightStyle } from '@codemirror/theme-one-dark';
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
      fontSize: '0.88rem',
      border: '1px solid var(--color-border-surface)',
      borderRadius: '10px',
      backgroundColor: 'var(--color-bg-surface)',
      color: 'var(--color-text)'
    },
    '.cm-content': {
      fontFamily: "'SFMono-Regular', Consolas, monospace",
      padding: '10px 0'
    },
    '.cm-scroller': {
      overflow: 'auto'
    },
    '.cm-gutters': {
      backgroundColor: 'var(--color-bg-surface)',
      color: 'var(--color-text-muted)',
      border: 'none'
    },
    '&.cm-focused': {
      outline: 'none'
    },
    // CodeMirror's own active-line highlight defaults to hardcoded light colors that clash with
    // dark mode — override with a theme-aware accent tint instead.
    '.cm-activeLine': {
      backgroundColor: 'color-mix(in srgb, var(--color-accent) 8%, transparent)'
    },
    '.cm-activeLineGutter': {
      backgroundColor: 'color-mix(in srgb, var(--color-accent) 14%, transparent)'
    }
  });

  function highlightExtensionFor(themeName) {
    return themeName === 'dark'
      ? syntaxHighlighting(oneDarkHighlightStyle, { fallback: true })
      : syntaxHighlighting(defaultHighlightStyle, { fallback: true });
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
