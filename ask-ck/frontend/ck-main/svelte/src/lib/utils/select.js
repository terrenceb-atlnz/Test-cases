// @ts-nocheck

// "Copy" on Ask CK means SELECT, never a clipboard write (2026-10-30, PLAN-svelte-cutover §2 #4).
//
// Ask CK is served over plain http from a LAN address, which is not a secure context:
// navigator.clipboard is undefined on every real seat, and the legacy document.execCommand('copy')
// fails on every seat Terrence has tried as well. The one thing that works everywhere with no
// per-seat configuration is to put the text in front of the user, selected, and say
// "press Ctrl+C". So every copy button in this app calls selectForCopy() and shows SELECTED_HINT.

export const SELECTED_HINT = "Selected — press Ctrl+C";

/** Select the whole content of `el` (an <input>/<textarea> by .select(), anything else by a DOM
 *  Range) so a Ctrl+C copies it. Returns false when there is nothing to select. */
export function selectForCopy(el) {
  if (!el) return false;
  if (typeof el.select === "function") {
    el.focus();
    el.select();
    return true;
  }
  const sel = window.getSelection && window.getSelection();
  if (!sel) return false;
  const range = document.createRange();
  range.selectNodeContents(el);
  sel.removeAllRanges();
  sel.addRange(range);
  return true;
}
