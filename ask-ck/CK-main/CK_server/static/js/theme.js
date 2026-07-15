// Light / Dark mode toggle (aligned with design system). Side-effect module.
// Light / Dark mode toggle (aligned with design system)
(function() {
  const root = document.documentElement;
  const toggle = document.getElementById('theme-toggle');
  const icon = document.getElementById('theme-icon');

  function setTheme(theme) {
    if (theme === 'light') {
      root.classList.remove('dark');
      root.classList.add('light');
      if (icon) icon.textContent = '☀️';
    } else {
      root.classList.remove('light');
      root.classList.add('dark');
      if (icon) icon.textContent = '🌙';
    }
    localStorage.setItem('theme', theme);
  }

  // Initialize theme
  const saved = localStorage.getItem('theme');
  if (saved) {
    setTheme(saved);
  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
    setTheme('light');
  } else {
    setTheme('dark');
  }

  if (toggle) {
    toggle.addEventListener('click', () => {
      const isLight = root.classList.contains('light');
      setTheme(isLight ? 'dark' : 'light');
    });
  }
})();
