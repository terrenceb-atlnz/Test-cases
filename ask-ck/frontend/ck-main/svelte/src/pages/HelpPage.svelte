<script>
  import chevronRightIcon from '../assets/icons/chevron-right.svg';
  import PageHeader from '../lib/components/PageHeader.svelte';
  import Button from '../lib/components/Button.svelte';

  const seatSetupWindowsCmd = 'irm http://…/setup/setup.ps1 | iex';
  const seatSetupUbuntuCmd = 'curl -fsSL http://…/setup/setup.sh | bash';

  let windowsCopyLabel = 'Copy';
  let ubuntuCopyLabel = 'Copy';

  async function copySetupCommand(text, which) {
    const setLabel = which === 'windows' ? (v) => (windowsCopyLabel = v) : (v) => (ubuntuCopyLabel = v);
    try {
      await navigator.clipboard.writeText(text);
      setLabel('Copied!');
    } catch (e) {
      setLabel('Copy failed');
    }
    setTimeout(() => setLabel('Copy'), 1500);
  }

  const toolGuides = [
    {
      title: 'Objective / Test Case Generator',
      content: `<p>The original Ask CK tool. Turns a sparse AWPTCM manual case into a refined case with declarative objectives, Zephyr-ready test steps, and traceability — with a review gate at every step.</p>
<ol>
  <li><strong>Cases</strong> — pick a case from the Open/partial or Complete dropdown and Load it.</li>
  <li><strong>TestLink</strong> — review the primary decision and candidate historical cases; Search or Suggest with the LLM, then Confirm your selections.</li>
  <li><strong>Zephyr</strong> — review related external Zephyr cross-references; Confirm.</li>
  <li><strong>ATPyLib (scored)</strong> — review the scored automation-coverage candidates and Confirm which ART suites apply.</li>
  <li><strong>Objectives (LLM)</strong> — synthesize the declarative objective artefacts from the confirmed reviews; edit, then Confirm.</li>
  <li><strong>Test Steps (LLM)</strong> — synthesize the Zephyr test steps from the finalized objective, then <strong>Export the Repeatable Bundle</strong> — this writes <code>traceability.md</code> + <code>zephyr_payload.json</code> into <code>refined-cases/&lt;Group&gt;/</code>. A case becomes "Complete" once this exists.</li>
</ol>`
    },
    { title: 'PyTest Creator',
      content: `<p>Turns a <strong>Complete</strong> case (one exported by the Generator above) into a runnable
Allied Telesis <code>framework</code> (ATTestSet/ATTestCase) test script, then runs it on
real hardware and iterates until it passes. Each step has a Confirm gate.</p>
<ol>
  <li><strong>Cases</strong> — pick a Complete case and Load it (use <strong>↻ Refresh list</strong> after exporting new cases in the Generator).</li>
  <li><strong>Sequence</strong> — the LLM extracts a prescriptive sequence of automatable steps from the refined case; edit the rows, Save, then Confirm.</li>
  <li><strong>Script Search</strong> — search the script databases (testsuites_art / svt_scripts / test_scripts) for scripts that do all, some, or none of the sequence; tick what to reuse, then Confirm.</li>
  <li><strong>Fragments</strong> — gather reusable code from the selected scripts (resolved to real source), untick what you don't want, then Confirm.</li>
  <li><strong>Generate</strong> — the LLM fills the standardized skeleton template from the fragments + gap-fill; edit the Group/name, Lint, Save to <code>generated/&lt;Group&gt;/</code>, then Confirm.</li>
  <li><strong>Run</strong> — pick a stored testbox (or add one under <strong>Testboxes</strong>), choose the .setup, and run it over SSH; results are parsed into per-TestCase PASS/FAIL.</li>
  <li><strong>Validate</strong> — Final Validation passes when every TestCase is PASS with zero failures. On failures, <strong>Fix with LLM</strong> loops back to Generate; promotion into <code>testsuites_art/</code> is manual.</li>
</ol>`
    },
    { title: 'Test Composer', content: '' },
    { title: 'Zephyr Templating', content: '' }
  ];

  const faqs = [
    { title: 'Which LLM provider should I use?', content: '' },
    { title: 'How do I configure my LLM settings?', content: '' },
    { title: 'What are the system requirements for running the workbench?', content: '' },
    { title: 'How often should I update my LLM model?', content: '' }
  ];

  let setupGuideOpen = false;

  /**
     * @type {number | null}
     */
  let openToolGuide = null;
  /**
     * @type {number | null}
     */
  let openFaq = null;

  /**
     * @param {string} group
     * @param {number | null} index
     */
  function toggle(group, index) {
    if (group === 'guide') {
      openToolGuide = openToolGuide === index ? null : index;
    } else {
      openFaq = openFaq === index ? null : index;
    }
  }
</script>

<PageHeader title="Help" intro="Find how to use the workbench via the guides provided below." />

<div class="help-page">

  <section class="help-section">
    <h2>Setup Guides</h2>
    <p class="help-section-intro">Get your environment ready before using the tools.</p>

    <div class="accordion">
      <div class="accordion-item">
        <button
          type="button"
          class="accordion-row"
          aria-expanded={setupGuideOpen}
          on:click={() => (setupGuideOpen = !setupGuideOpen)}
        >
          <span>Set up your seat for Claude</span>
          <img class="chevron" class:open={setupGuideOpen} src={chevronRightIcon} alt="" aria-hidden="true" />
        </button>
        {#if setupGuideOpen}
          <div class="accordion-panel">
            <p>Ask CK runs in your browser; it <strong>cannot run Claude on your PC by itself</strong>.
              A small agent on your PC does that, using <strong>your own</strong> Claude seat —
              nothing is shared and the server never sees a credential. One line installs Claude
              Code if needed, fixes your PATH, logs you in, installs the agent and starts it.
              Re-run the same line any time to update or repair.</p>
            <ol>
              <li>
                <strong>Windows</strong> — open <strong>PowerShell</strong> and paste:
                <div class="copy-field-row">
                  <div class="copy-field-box">{seatSetupWindowsCmd}</div>
                  <Button variant="primary" copy on:click={() => copySetupCommand(seatSetupWindowsCmd, 'windows')}>
                    {windowsCopyLabel}
                  </Button>
                </div>
                <span class="justification-note">(or <a href="/setup/setup.ps1" download>download setup.ps1</a>
                  and run it with <code>powershell -ExecutionPolicy Bypass -File setup.ps1</code>)</span>
              </li>
              <li>
                <strong>Ubuntu</strong> — open a terminal and paste:
                <div class="copy-field-row">
                  <div class="copy-field-box">{seatSetupUbuntuCmd}</div>
                  <Button variant="primary" copy on:click={() => copySetupCommand(seatSetupUbuntuCmd, 'ubuntu')}>
                    {ubuntuCopyLabel}
                  </Button>
                </div>
                <span class="justification-note">(or <a href="/setup/setup.sh" download>download setup.sh</a>)</span>
              </li>
              <li>It asks once whether the agent should start when you log in, then opens Ask CK,
                which runs the final check itself — the result appears under <strong>LLM → Configure</strong>.
                Pick <strong>Claude Code CLI (my local machine)</strong> there and you are ready.</li>
            </ol>
          </div>
        {/if}
      </div>
    </div>
  </section>

  <section class="help-section">
    <h2>Tool Guides</h2>
    <p class="help-section-intro">Learn how to use the Ask CK workbench tools.</p>

    <div class="accordion">
      {#each toolGuides as guide, i}
        <div class="accordion-item">
          <button
            type="button"
            class="accordion-row"
            aria-expanded={openToolGuide === i}
            on:click={() => toggle('guide', i)}
          >
            <span>{guide.title}</span>
            <img class="chevron" class:open={openToolGuide === i} src={chevronRightIcon} alt="" aria-hidden="true" />
          </button>
          {#if openToolGuide === i}
            <div class="accordion-panel">
              {#if guide.content}
                {@html guide.content}
              {:else}
                <p>Content coming soon.</p>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  </section>

  <section class="help-section">
    <h2>FAQs</h2>

    <div class="accordion">
      {#each faqs as faq, i}
        <div class="accordion-item">
          <button
            type="button"
            class="accordion-row"
            aria-expanded={openFaq === i}
            on:click={() => toggle('faq', i)}
          >
            <span>{faq.title || 'FAQ ' + (i + 1)}</span>
            <img class="chevron" class:open={openFaq === i} src={chevronRightIcon} alt="" aria-hidden="true" />
          </button>
          {#if openFaq === i}
            <div class="accordion-panel">
              {#if faq.content}
                {@html faq.content}
              {:else}
                <p>Content coming soon.</p>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  </section>

  <p class="help-contact">
    For any technical issues, please contact <strong>Terrence Beach</strong> at
    <a href="mailto:terrence.beach@alliedtelesis.co.nz">terrence.beach@alliedtelesis.co.nz</a>.
  </p>
</div>

<style>
  .help-page {
    max-width: 760px;
    margin: 0 auto;
    padding-top: 16px;
  }

  .help-section {
    margin-bottom: 32px;
  }

  .help-section h2 {
    margin: 0 0 4px;
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--color-text-heading);
  }

  .help-section-intro {
    margin: 0 0 14px;
    color: var(--color-text-muted);
    font-size: 0.92rem;
  }

  .accordion {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .accordion-item {
    border: 1px solid var(--color-border-surface);
    border-radius: 10px;
    background: var(--color-bg-surface);
    overflow: hidden;
    transition: background-color 0.2s ease, border-color 0.2s ease;
  }

  .accordion-row {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 18px;
    background: transparent;
    border: none;
    font: inherit;
    font-weight: 600;
    color: var(--color-text-heading);
    text-align: left;
    cursor: pointer;
  }

  .accordion-row:hover {
    background: rgba(0, 83, 143, 0.05);
  }

  .chevron {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    filter: var(--icon-filter-muted);
    transition: transform 0.2s ease, filter 0.2s ease;
  }

  .chevron.open {
    transform: rotate(90deg);
  }

  .accordion-panel {
    padding: 10px 18px 16px;
    color: var(--color-text-muted);
    font-size: 0.94rem;
  }

  .accordion-panel :global(p) {
    margin: 0 0 12px;
  }

  .accordion-panel :global(p:last-child) {
    margin-bottom: 0;
  }

  .accordion-panel :global(ol) {
    margin: 0;
    padding-left: 20px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .accordion-panel :global(li) {
    line-height: 1.5;
  }

  .accordion-panel :global(strong) {
    color: var(--color-text-heading);
  }

  .accordion-panel :global(code) {
    background: var(--color-code-bg);
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 0.88em;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }

  .copy-field-row {
    display: flex;
    align-items: stretch;
    gap: 10px;
    margin: 8px 0;
  }

  .copy-field-box {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    padding: 8px 12px;
    border-radius: 8px;
    border: 1px solid var(--color-border-surface);
    background: var(--color-code-bg);
    color: var(--color-text);
    font-size: 0.88em;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    overflow-x: auto;
    white-space: nowrap;
  }

  .justification-note {
    display: block;
    margin-top: 4px;
    font-size: 0.88em;
  }

  .help-contact {
    margin-top: 12px;
    color: var(--color-text-muted);
    font-size: 0.92rem;
  }

  .help-contact a {
    color: var(--color-accent);
  }
</style>
