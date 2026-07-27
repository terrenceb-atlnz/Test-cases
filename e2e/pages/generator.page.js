// Page Object for the Objective/Test-Case Generator golden journey.
// ALL selectors live here so DOM churn in index.html is a one-file fix.
// Selectors were grounded in the real markup (index.html) + render code
// (static/js/tables.js, db-search.js, generator.js) on 2026-07-27 — not guessed.
import { expect } from '@playwright/test';

// The three DB-search "kinds" share an identical structure; drive them by config.
export const KINDS = {
  testlink: {
    step: 1,
    searchInput: '#tlSearchQ',
    searchAction: '[data-action="searchTestLink"]',
    table: '#tl-table',
    chosenTable: '#tl-chosen-table',
    topCheckbox: 'input.tl-checkbox',
    chooseAction: '[data-action="chooseTestLink"]',
  },
  zephyr: {
    step: 2,
    searchInput: '#zephyrSearchQ',
    searchAction: '[data-action="searchZephyr"]',
    table: '#zephyr-table',
    chosenTable: '#zephyr-chosen-table',
    topCheckbox: 'input.zephyr-checkbox',
    chooseAction: '[data-action="chooseZephyr"]',
  },
  atp: {
    step: 3,
    searchInput: '#atpSearchQ',
    searchAction: '[data-action="searchATP"]',
    table: '#atp-table',
    chosenTable: '#atp-chosen-table',
    topCheckbox: 'input.atp-checkbox',
    chooseAction: '[data-action="chooseATP"]',
  },
};

export class GeneratorPage {
  constructor(page) {
    this.page = page;
  }

  async open() {
    await this.page.goto('/');
    // Cold load lands on panel-main; wait for the app shell to be interactive.
    await expect(this.page.locator('#nav-generator')).toBeAttached();
    await this.expandGeneratorSection();
  }

  // The sidebar is an accordion, all sections collapsed on load (nav.js). The
  // Generator's step items live in a collapsed section and aren't clickable until
  // their section label is clicked open. Match the label by its fixed display text.
  async expandGeneratorSection() {
    const label = this.page.locator('.sidebar-section-label', {
      hasText: 'Objective/Test Case Generator',
    });
    // Idempotent: only click to open if a step item isn't already visible.
    const firstStep = this.page.locator('[data-action="goToStep"][data-step="0"]');
    if (!(await firstStep.isVisible())) await label.click();
    await expect(firstStep).toBeVisible();
  }

  // Navigate to a Generator step. data-step ids are 0..5 (off-by-one vs the
  // "1. Cases … 6." sidebar labels); goToStep(n) drives that dispatcher directly.
  async goToStep(step) {
    await this.expandGeneratorSection();
    await this.page.locator(`[data-action="goToStep"][data-step="${step}"]`).click();
    await expect(this.page.locator(`#step-${step}`)).toBeVisible();
  }

  // Select an open/partial case in the real dropdown and click Load.
  async loadCase(caseKey) {
    await this.goToStep(0);
    await this.page.locator('#caseSelOpen').selectOption(caseKey);
    await this.page.locator('[data-action="loadCase"]').click();
    // #load-status is hidden again in the handler's finally block, so it's not a
    // reliable signal. A *successful* load's real side effect is updateUI() writing
    // the full session JSON (incl. the case key) into #session-view — wait on that.
    await expect(this.page.locator('#session-view')).toContainText(caseKey, {
      timeout: 15_000,
    });
  }

  // Keyword-search a kind, then Choose the first N result rows into its chosen table.
  // Returns the number of rows actually chosen (so the caller can assert > 0).
  // Asserts the chosen table grew by exactly the number ticked — an in-progress
  // case can load with pre-existing chosen rows, so we measure the DELTA, not an
  // absolute count.
  async searchAndChoose(kindName, query, take = 2) {
    const k = KINDS[kindName];
    await this.goToStep(k.step);

    const chosen = this.page.locator(`${k.chosenTable} input[type="checkbox"]`);
    const before = await chosen.count();

    await this.page.locator(k.searchInput).fill(query);
    await this.page.locator(k.searchAction).click();

    // Wait for the candidates table to have at least one row's checkbox rendered.
    const boxes = this.page.locator(`${k.table} ${k.topCheckbox}`);
    await expect(boxes.first()).toBeVisible({ timeout: 15_000 });

    const available = await boxes.count();
    const n = Math.min(take, available);
    for (let i = 0; i < n; i++) await boxes.nth(i).check();

    await this.page.locator(k.chooseAction).click();

    // Chosen table should grow by exactly the number ticked (rows moved from the
    // candidates table into the chosen table via chooseSelected()).
    await expect(chosen).toHaveCount(before + n, { timeout: 10_000 });
    return n;
  }

  // Click the always-present Export button in the Cases panel (step-0).
  async exportFromCasesPanel() {
    await this.goToStep(0);
    await this.page.locator('#step-0 [data-action="exportBundle"]').click();
  }

  statusBanner() {
    return this.page.locator('#export-status');
  }
}
