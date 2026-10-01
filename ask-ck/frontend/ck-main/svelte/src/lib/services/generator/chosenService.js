// COPIED OVER FROM current/generator/chosen.js (restore slice only — chooseSelected/
// clearSelected/chooseByIds stay inline in CandidatePickerStep.svelte, which already owns
// that state; this is just the id-indexed restore logic all three candidate steps share)

// MODIFIED FROM current/generator/chosen.js's restoreChosenFromSelections TO WORK WITH
// SVELTE (that wrote straight into window[chosenBus] and re-rendered the DOM table; this
// just returns the reconstructed array for the component to bind).
//
// Re-populates a step's chosen list from persisted session selections (on load/restore).
// Enriches each selection with the FULL candidate record when it's still present in the
// currently-loaded candidate pool (richer score/description), else falls back to a minimal
// record built from the selection's own saved fields. Order is preserved from the
// persisted `order` field, falling back to list position for older sessions saved before
// it existed.
export function restoreChosen(selections, candidates) {
  const sels = Array.isArray(selections) ? selections : [];
  const byId = new Map((candidates || []).map((c) => [c.id, c]));
  const withOrder = sels.map((s, i) => ({ s, o: typeof s.order === 'number' ? s.order : i }));
  withOrder.sort((a, b) => a.o - b.o);
  return withOrder.map(({ s }) => {
    const id = s.id_or_key || s.id;
    return byId.get(id) || {
      id,
      title: s.title || id,
      description: s.justification || '',
      justification: s.justification || '',
      score: s.score,
    };
  });
}
