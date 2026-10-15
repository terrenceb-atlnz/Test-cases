<script>
// @ts-nocheck

  // A step / unit status as an icon: Confirmed (circle-check), In Review (circle-alert),
  // Not started (circle-minus), Critical (circle-x). The icons are currentColor SVGs shown via
  // <img>, which draw black — so each status is tinted by a CSS filter, read from the
  // --filter-status-* variables in app.css (computed per theme to match its colour tokens).
  import checkIcon from '../../assets/icons/circle-check.svg';
  import alertIcon from '../../assets/icons/circle-alert.svg';
  import minusIcon from '../../assets/icons/circle-minus.svg';
  import xIcon from '../../assets/icons/circle-x.svg';

  /** @type {'covered' | 'review' | 'none' | 'error'} The step / unit status, as the arrow
      steps use it — 'error' is a unit with a high-severity review finding. */
  export let status = 'none';

  const ICONS = { covered: checkIcon, review: alertIcon, none: minusIcon, error: xIcon };

  $: known = ICONS[status] ? status : 'none';
</script>

<img class="status-badge status-{known}" src={ICONS[known]} alt="" aria-hidden="true" />

<style>
  .status-badge {
    flex: 0 0 auto;
    width: 22px;
    height: 22px;
    margin-top: 2px;
  }

  .status-covered { filter: var(--filter-status-covered); }
  .status-review { filter: var(--filter-status-review); }
  .status-none { filter: var(--filter-status-none); }
  .status-error { filter: var(--filter-status-error); }
</style>
