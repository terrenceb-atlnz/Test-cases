<div class="under-construction">
  <!-- Inlined from assets/icons/construction.svg with stroke swapped to currentColor so it follows
       the muted text color here (and the light/dark theme) without a dynamic url()/mask. -->
  <svg
    class="under-construction-icon"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <rect x="2" y="6" width="20" height="8" rx="1" />
    <path d="M17 14v7" />
    <path d="M7 14v7" />
    <path d="M17 3v3" />
    <path d="M7 3v3" />
    <path d="M10 14 2.3 6.3" />
    <path d="m14 6 7.7 7.7" />
    <path d="m8 6 8 8" />
  </svg>
  <p class="under-construction-title">UNDER CONSTRUCTION</p>
</div>

<style>
  .under-construction {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 18px;
    width: 300px;
    height: 300px;
    margin: 60px auto;
    border: 5px dashed var(--color-border-surface);
    border-radius: 32px;
    color: var(--color-text-muted);
  }

  .under-construction-icon {
    width: 100px;
    height: auto;
    flex-shrink: 0;
  }

  .under-construction-title {
    margin: 0;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--color-text-muted);
  }
</style>
