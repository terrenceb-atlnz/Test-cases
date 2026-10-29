import { tick } from "svelte";

// @ts-nocheck
// Waits for Svelte to flush the pending DOM update (a step/unit swap) before scrolling —
// otherwise this can run while the old, taller content is still on screen, and the subsequent
// layout shift from the swap interrupts or swallows the smooth-scroll animation.

// Used by the main "Review & Confirm" actions (one step -> the next main step) — goes all the
// way to the top of the page.
export async function scrollToTop() {
  await tick();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// Scrolls to the very bottom of the page — used after moving rows into a Chosen table
// further down the panel (e.g. "Choose selected"), so the result of the action is visible
// without the user having to scroll down manually to find it.
export async function scrollToBottom() {
  await tick();
  window.scrollTo({
    top: document.documentElement.scrollHeight,
    behavior: "smooth",
  });
}

/**
 * @param {string} section
 */
export async function scrollToSection(section) {
  await tick();
  const intro = document.querySelector(section);
  if (intro) {
    intro.scrollIntoView({ behavior: "smooth", block: "start" });
  } else {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}
