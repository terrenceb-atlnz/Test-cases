// Builds the Svelte islands into ../islands/ (PLAN-test-composer §6, decision C-D1).
//
// One entry per island; each is an ES module the plain current/ modules import at run time
// (`import('../islands/zt.js')`). The output is COMMITTED: the hosted server only serves files
// (no build step, no Node at run time), and the working tree is production.
//
// Every bundle opens with `source-sha256:<hex>`: the hash of this directory's sources (src/**,
// this file, package.json, package-lock.json). tests/test_svelte_islands_built.py recomputes it
// and fails the gate when the committed bundle was not rebuilt after a source change.
import { createHash } from 'node:crypto';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';

const HERE = dirname(fileURLToPath(import.meta.url));

function files(dir) {
  return readdirSync(dir).flatMap(n => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? files(p) : [p];
  });
}

/** sha256 over the sorted (relative path, contents) of every source — mirrored in Python. */
export function sourceHash() {
  const list = [...files(join(HERE, 'src')),
    ...['vite.config.js', 'package.json', 'package-lock.json'].map(n => join(HERE, n))]
    .map(p => relative(HERE, p).split('\\').join('/')).sort();
  const h = createHash('sha256');
  for (const rel of list) {
    h.update(rel + '\n');
    h.update(readFileSync(join(HERE, rel)));
    h.update('\n');
  }
  return h.digest('hex');
}

export default defineConfig({
  plugins: [svelte({ compilerOptions: { runes: true } })],
  build: {
    outDir: resolve(HERE, '../islands'),
    emptyOutDir: true,
    minify: false,
    sourcemap: false,
    lib: {
      entry: { zt: resolve(HERE, 'src/zt/main.js') },
      formats: ['es'],
      fileName: (_format, name) => `${name}.js`,
    },
    rollupOptions: {
      output: {
        banner: `/* Built from ask-ck/frontend/ck-main/current/svelte-src/ — do not edit; run \`npm run build\` there.\n`
          + ` * source-sha256:${sourceHash()} */`,
      },
    },
  },
});
