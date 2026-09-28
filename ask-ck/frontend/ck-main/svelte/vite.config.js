import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  server: {
    // The real backend runs as its own FastAPI process (CK_server/main.py, default port
    // 8000) — proxying /api makes the browser see everything as same-origin, so the ported
    // session/LLM header logic (src/lib/api/client.js) needs no CORS special-casing.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
