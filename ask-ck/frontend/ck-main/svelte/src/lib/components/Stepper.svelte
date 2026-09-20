<script>
  import arrowRightIcon from '../../assets/icons/arrow-right.svg';

  /** @type {Array<{ id: string, label: string, icon?: string }>} */
  export let steps = [];

  /** @type {number} Index of the current step */
  export let currentStep = 0;

  /** @type {number} Furthest step index reached so far (stays put when navigating back) */
  export let maxStepReached = 0;

  /** @type {((index: number) => void) | null} Called when a visited step's node is clicked */
  export let onStepClick = null;
</script>

<div class="stepper">
  {#each steps as step, i}
    <div
      class="stepper-step"
      class:completed={i !== currentStep && i <= maxStepReached}
      class:current={i === currentStep}
    >
      <button
        type="button"
        class="stepper-node"
        class:completed={i !== currentStep && i <= maxStepReached}
        class:current={i === currentStep}
        class:pending={i > maxStepReached}
        disabled={!(onStepClick && i !== currentStep && i <= maxStepReached)}
        on:click={() => onStepClick && i !== currentStep && i <= maxStepReached && onStepClick(i)}
        aria-current={i === currentStep ? 'step' : undefined}
        aria-label={step.label}
      >
        <img class="stepper-icon" src={step.icon || arrowRightIcon} alt="" aria-hidden="true" />
      </button>
      <span class="stepper-label" class:current={i === currentStep}>{i + 1}. {step.label}</span>
    </div>
  {/each}
</div>

<style>
  .stepper {
    display: flex;
    width: 100%;
    margin-bottom: 24px;
    margin-top: 2rem;
  }

  .stepper-step {
    position: relative;
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
  }

  .stepper-step {
    --stepper-node-radius: 2rem;
    --stepper-line-gap: 10px;
  }

  .stepper-step:not(:first-child)::before {
    content: '';
    position: absolute;
    top: 2rem;
    left: calc(-50% + var(--stepper-node-radius) + var(--stepper-line-gap));
    width: calc(100% - (2 * (var(--stepper-node-radius) + var(--stepper-line-gap))));
    height: 4px;
    background: var(--color-stepper-outline);
    z-index: 0;
  }

  .stepper-step:not(:first-child)::after {
    content: '';
    position: absolute;
    top: 2rem;
    left: calc(-50% + var(--stepper-node-radius) + var(--stepper-line-gap));
    width: calc(100% - (2 * (var(--stepper-node-radius) + var(--stepper-line-gap))));
    height: 4px;
    background: var(--color-accent);
    transform: scaleX(0);
    transform-origin: left;
    transition: transform 0.5s ease-out;
    z-index: 0;
  }

  .stepper-step:is(.completed, .current):not(:first-child)::after {
    transform: scaleX(1);
  }

  .stepper-node {
    position: relative;
    z-index: 1;
    width: 4rem;
    height: 4rem;
    border-radius: 50%;
    border: 4px solid var(--color-stepper-outline);
    background: var(--color-bg-content);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    cursor: default;
    transition: background-color 0.2s ease, border-color 0.5s ease;
  }

  .stepper-node.current {
    border-color: var(--color-accent);
    /* background: var(--color-accent); */
  }

  .stepper-node.completed {
    border-color: var(--color-accent);
    background: var(--color-accent);
    cursor: pointer;
  }

  .stepper-node.completed:hover {
    filter: brightness(1.1);
  }

  .stepper-icon {
    width: 1.5rem;
    height: 1.5rem;
    filter: var(--icon-filter-muted);
    transition: filter 0.2s ease;
  }

  .stepper-node.current .stepper-icon {
    filter: var(--icon-filter-node-current);
  }

  .stepper-node.completed .stepper-icon {
    filter: var(--icon-filter-node-completed);
  }

  .stepper-label {
    font-size: 0.9rem;
    color: var(--color-stepper-outline);
    font-weight: 600;
    text-align: center;
  }

  .stepper-label.current {
    color: var(--color-text-heading);
    font-weight: 700;
  }
</style>
