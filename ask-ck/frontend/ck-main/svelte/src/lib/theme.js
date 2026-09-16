import { writable } from 'svelte/store';

const STORAGE_KEY = 'askck-theme';

function getInitial() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
  } catch (e) {
    // localStorage unavailable (private browsing, etc.) — fall through to default
  }
  return 'system';
}

function systemPrefersDark() {
  return typeof window !== 'undefined' && window.matchMedia
    ? window.matchMedia('(prefers-color-scheme: dark)').matches
    : false;
}

export const theme = writable(getInitial());

/** The theme actually in effect: 'light' or 'dark', with 'system' already resolved. */
export const resolvedTheme = writable(systemPrefersDark() ? 'dark' : 'light');

export function setTheme(value) {
  theme.set(value);
  try {
    localStorage.setItem(STORAGE_KEY, value);
  } catch (e) {
    // ignore write failures
  }
}

if (typeof document !== 'undefined') {
  let currentTheme = 'system';
  const mql = window.matchMedia('(prefers-color-scheme: dark)');

  function applyResolved() {
    resolvedTheme.set(currentTheme === 'system' ? (mql.matches ? 'dark' : 'light') : currentTheme);
  }

  theme.subscribe((value) => {
    currentTheme = value;

    const root = document.documentElement;
    if (value === 'system') {
      root.removeAttribute('data-theme');
    } else {
      root.setAttribute('data-theme', value);
    }

    applyResolved();
  });

  mql.addEventListener('change', applyResolved);
}
