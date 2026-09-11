// Shared mutable app state. Replaces the five bare module-scope globals that
// used to live at the top of app.js; ESM imported bindings are read-only, so
// cross-module writes go through this object's properties instead.
//
// KNOWN DEBT (unchanged this pass): a second bus still lives on `window.*` —
// window.currentTestLink / currentZephyr / currentATP / currentCaseTitle /
// lastLLMConfig. Every use is already `window.`-prefixed, so migrating it here
// later is a mechanical sed. See static/js/README.md.
export const S = {
  currentSession: null,
  currentKey: null,
  currentStep: 0,
  currentPanel: 'step-0',
  // PyTest Creator selection — deliberately separate from currentKey (the Generator's loaded case)
  ptCase: { key: null, title: null },
};
