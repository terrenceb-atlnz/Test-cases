// Pass C in the UI (PLAN-pytest-creator.md §9.6, 2026-09-02).
//
// The review reports FINDINGS and never rewrites the script. That decision has a UI
// consequence worth pinning: there is deliberately NO "apply" affordance on this panel.
// A finding becomes a change through the step-7 Fix loop, where it is a recorded,
// reviewable action — §9.6 rejects a rewrite pass because it re-emits the whole file
// (the wall clock chunking exists to avoid) and can silently undo a reused fragment,
// breaking the provenance chain PLAN §1.5 keeps.
//
// Also pinned: "no findings" must render as a RESULT, not as an empty panel. A blank
// div is indistinguishable from a review that never ran, and the reviewer would have no
// way to tell a clean script from a broken button.
//
// Source-level, matching the other pt specs. Comments are stripped before every
// assertion — this file's prose names the identifiers it forbids.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const read = (rel) => readFileSync(resolve(HERE, rel), 'utf8');
const JS = read('../ask-ck/CK-main/CK_server/static/js/pytest.js')
  .replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
const HTML = read('../ask-ck/CK-main/CK_server/static/index.html')
  .replace(/<!--[\s\S]*?-->/g, '');
const CSS = read('../ask-ck/CK-main/CK_server/static/styles.css');

const RENDER = JS.slice(JS.indexOf('function ptRenderReview'),
                        JS.indexOf('async function ptReviewScript'));
const HANDLER = JS.slice(JS.indexOf('async function ptReviewScript'),
                         JS.indexOf('async function ptGenerateScript'));

describe('review panel wiring', () => {
  it('has a button that reaches the registered action', () => {
    expect(HTML).toContain('data-action="ptReviewScript"');
    expect(HTML).toContain('id="pt-review-btn"');
    expect(HTML).toContain('id="pt-review-result"');
    expect(JS).toMatch(/registerActions\([\s\S]*ptReviewScript/);
  });

  it('treats the review as the LLM call it is', () => {
    // Without llm:true there is no live progress and no working Stop — on a script this
    // size that is a button that appears dead for minutes.
    expect(HANDLER).toContain('llm: true');
    expect(HANDLER).toContain('btn');
    expect(HANDLER).toContain('recordLLMDebug');
  });

  it('pushes editor edits before reviewing, exactly as Lint does', () => {
    // Reviewing the session copy while the textarea holds something else reports
    // findings against a script the reviewer cannot see.
    expect(HANDLER).toContain('ptPushCodeEdits');
  });

  it('re-seeds the findings from the session on panel render', () => {
    // A reload must not discard findings the reviewer paid an LLM call for.
    const panel = JS.slice(JS.indexOf('export function renderPtGenPanel'),
                           JS.indexOf('export async function renderPtRunPanel'));
    expect(panel).toContain('ptRenderReview');
    expect(panel).toContain('s6.review');
  });
});

describe('what the panel refuses to offer', () => {
  it('offers no way to apply a finding directly to the script', () => {
    // §9.6: findings route through the Fix loop. An apply button here would be a
    // rewrite pass wearing a review's name.
    expect(HANDLER).not.toMatch(/save_script|generate_script|fix_script/);
    expect(RENDER).not.toMatch(/data-action="pt(Apply|Fix|Save)/);
  });

  it('does not write the code textarea', () => {
    expect(RENDER).not.toContain('pt-gen-code');
    expect(HANDLER).not.toContain('pt-gen-code');
  });
});

describe('rendering', () => {
  it('renders "no findings" as a result, not as an empty panel', () => {
    expect(RENDER).toContain('no findings');
    expect(RENDER).toMatch(/findings\.length/);
  });

  it('distinguishes a clean review from one that never ran', () => {
    // review.at is the discriminator: absent = never reviewed, present + empty = clean.
    expect(RENDER).toMatch(/review\.at/);
  });

  it('escapes every model-authored field it renders', () => {
    // Findings are LLM text quoting the script back; `evidence` is verbatim source.
    for (const f of ['f.what', 'f.evidence', 'f.suggestion', 'f.where', 'f.kind']) {
      const re = new RegExp(`escapeHtml\\(${f.replace('.', '\\.')}`);
      expect(RENDER, `${f} must be escaped`).toMatch(re);
    }
  });

  it('points the reviewer at where a finding gets acted on', () => {
    expect(RENDER).toMatch(/step 7|Validate/);
  });

  it('has a severity style for each level the backend can emit', () => {
    for (const sv of ['high', 'medium', 'low']) {
      expect(CSS).toContain(`.pt-review-${sv}`);
    }
  });
});
