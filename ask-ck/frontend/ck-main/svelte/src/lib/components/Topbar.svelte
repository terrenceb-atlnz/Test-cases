<script>
  import { resolvedTheme } from '../theme.js';
  import atLogoDark from '../../assets/at-logo.png';
  import atLogoLight from '../../assets/at-logo-light.png';

  $: brandLogo = $resolvedTheme === 'dark' ? atLogoLight : atLogoDark;
</script>

<header class="topbar">
  <div class="brand" aria-label="Allied Telesis home">
    <div class="brand-logo" aria-hidden="true">
      <img src={brandLogo} alt="Allied Telesis logo" />
    </div>
  </div>
</header>

<style>
  .topbar {
    grid-column: 2;
    grid-row: 1;
    height: 72px;
    background: var(--color-bg-topbar);
    border-bottom: 1px solid var(--color-border-topbar);
    display: flex;
    align-items: center;
    padding: 0 18px 0 24px;
    transition: background-color 0.2s ease, border-color 0.2s ease;
  }

  .brand {
    display: inline-flex;
    align-items: center;
    gap: 12px;
    color: var(--color-text-heading);
    font-weight: 600;
    font-size: 1.05rem;
  }

  .brand-logo img {
    width: auto;
    height: 3em;
    border-radius: 6px;
    object-fit: cover;
  }
</style>
