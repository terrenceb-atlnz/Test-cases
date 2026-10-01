import { tick } from 'svelte';

// Waits for Svelte to flush the pending DOM update (a step/unit swap) before scrolling —
// otherwise this can run while the old, taller content is still on screen, and the subsequent
// layout shift from the swap interrupts or swallows the smooth-scroll animation.

// Used by the main "Review & Confirm" actions (one step -> the next main step) — goes all the
// way to the top of the page.
export async function scrollToTop() {
  await tick();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Used when confirming an individual arrow step within a step's own arrow-stepper — goes to
// that step's own description just above its arrow-step row, rather than the page top, since
// that's the part actually relevant when paging between steps within the same arrow-stepper.
export async function scrollToStepIntro() {
  await tick();
  const intro = document.querySelector('.step-intro');
  if (intro) {
    intro.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } else {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

// Scrolls to the very bottom of the page — used after moving rows into a Chosen table
// further down the panel (e.g. "Choose selected"), so the result of the action is visible
// without the user having to scroll down manually to find it.
export async function scrollToBottom() {
  await tick();
  window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' });
}

// Generator-side equivalent of scrollToStepIntro — same reasoning, but for the Objective
// Generator's own step intro convention (.cases-intro, used by CasePicker/CandidatePickerStep/
// ObjectivesStep/TestStepsStep), which is a separate flow from PyTest Creator's arrow-stepper.
// Used after Search/Suggest populates a candidate table, so the refreshed panel is obviously
// visible even if the user was scrolled down reviewing the Chosen table below.
export async function scrollToCasesIntro() {
  await tick();
  const intro = document.querySelector('.cases-intro');
  if (intro) {
    intro.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } else {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}
