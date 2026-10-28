# Ask CK - Svelte Frontend GUI

<p align="center">
<img src="./src/assets/askck-logo.png" alt="Home page in light mode" width="150">
</p>

The Svelte frontend was created as a part of the BCIS309 Work Integrated Learning project under Ara Institute of Canterbury - Software Development student Trent Morgan. 
The project contains 7 pages, each with its own route. 4 of them are the original Ask CK tools, and 3 support them:

| Page | Route | What it is |
| --- | --- | --- |
| Home | `/` | Tool cards for each tool, and the hidden admin panel |
| Objective Generator | `/generator` | 6 steps |
| PyTest Creator | `/pytest` | 5 steps |
| Test Composer | `/composer` | 3 variations: Run Scripts, Compose a Run, Validate a Script |
| Zephyr Templating | `/zephyr` | 1 page |
| Settings | `/settings` | Theme, LLM configuration and the seat agent |
| Help | `/help` | Guides and seat agent setup |

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) with the following extensions:

- **[Svelte for VS Code](https://marketplace.visualstudio.com/items?itemName=svelte.svelte-vscode)** - syntax highlighting, intellisense and the Svelte compiler's warnings for `.svelte` files. `jsconfig.json` has `checkJs` on, so type problems in `.js` and `.svelte` files show up in the editor's Problems panel.
- **[Prettier](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode)** - code formatting, used throughout the frontend.
- **[Vitest](https://marketplace.visualstudio.com/items?itemName=vitest.explorer)** (optional) - run and debug individual specs from the editor's Testing panel.

The project needs **Node.js 22** and the Ask CK backend running on port `8000`, because the Vite dev server proxies `/api` to it. From this directory:

```bash
npm install --legacy-peer-deps   # the flag is needed for the current testing-library peer ranges
npm run dev                      # dev server at http://localhost:5173
npm test                         # Vitest, once
npm run test:watch               # Vitest in watch mode
npm run coverage                 # Vitest with a v8 coverage report in coverage/
npm run build                    # production build into dist/
```

## Project Structure

```text
src/
├── main.js             # mounts App.svelte; imports app.css and fonts.css
├── App.svelte          # the app shell (sidebar, topbar) and page switching by route
├── app.css             # global styles and the light/dark theme tokens (see Theming)
├── fonts.css, fonts/   # bundled Inter and Roboto Mono fonts
├── routes.js           # route paths for each page
├── pages/              # one component per page (HomePage, GeneratorPage, PyTestPage, ...)
└── lib/
    ├── api/client.js   # patches fetch so /api requests carry the session and LLM headers
    ├── components/     # shared components (Button, LlmButton, ErrorBanner, Stepper, Table, ...)
    │   ├── generator/      # Objective Generator steps   - prefix Og
    │   ├── pytest/         # PyTest Creator steps        - prefix Pt
    │   ├── testcomposer/   # Test Composer parts         - prefix Tc
    │   └── zephyr/         # Zephyr Templating parts     - prefix Zt
    ├── services/       # all server calls, grouped by tool like components/
    ├── utils/          # small helpers (scrolling)
    └── theme.js        # the light / dark / system theme store
```

Each part of the code has one job:

- **Pages** lay out a tool and hold its state.
- **Components** render and report user actions through `onX` callback props (for example `onConfirm`). Most leave server calls to their page; the exceptions are larger self-contained parts such as `AdminPanel` and the Test Composer pages, which call their service directly.
- **Services** (`lib/services/`) make the requests to the backend. One exception remains: `TcValidate.svelte` still has a direct `fetch` call.
- **Model files** (`*Model.js`, such as `generateModel.js`) hold pure logic with no Svelte or network code, so they can be unit tested on their own.

## Theming

All colours are CSS custom properties ("tokens") defined in `src/app.css`, and components use them instead of fixed colours, for example `color: var(--color-text-muted)`. The file has three token blocks:

1. **Light**, the default, on `:root`.
2. **Dark (system)**, which applies when the theme is "System" and the operating system is in dark mode.
3. **Dark (chosen)**, which applies when "Dark" is picked in Settings. `theme.js` sets `data-theme="dark"` on the page for this.

**The two dark blocks must stay identical.** CSS cannot share one block between a media query and an attribute selector, so a token changed in only one of them makes "System" and "Dark" look different.

To add a colour, add the token to all three blocks under the matching group comment, then use it with `var(--token-name)`. Icons are SVGs shown with `<img>`, so they are coloured with CSS filters; the `--filter-*` and `--icon-filter-*` tokens hold those, each with a comment naming the colour it produces.

## Testing

- **Where specs go:** `tests/` mirrors `src/`. For example, `src/lib/components/pytest/PtGenerate.svelte` is tested in `tests/components/pytest/PtGenerate.spec.js`.
- **Setup:** `tests/setup.js` runs before every spec and loads jest-dom, which adds matchers like `toBeInTheDocument()`. Vitest runs in jsdom, with `describe`, `it` and `expect` available globally.
- **Components** are tested with Testing Library: render the component with props, find elements the way a user would (`getByRole`, `getByText`, `getByPlaceholderText`), interact, then assert. Server calls are mocked with `vi.mock`.
- **Unwritten tests** are written as `describe.todo("")` or `it.todo("what it should do")`, never left as blank files (Vitest fails an empty spec file) or as placeholder tests that always pass. Vitest reports them as skipped or todo.
- **E2E:** `tests/e2e/` is set aside for Playwright and excluded from Vitest.

## Relationship to the Legacy Frontend

This app is a port of the original Ask CK frontend in `ask-ck/frontend/ck-main/current/` (plain JavaScript modules, plus Svelte islands in `current/svelte-src/`). Both frontends use the same FastAPI backend and the same `/api` endpoints.

- **The backend still serves the legacy frontend.** `CK_server/main.py` serves `current/`; it does not serve this app's `dist/` build yet.
- **This app runs through the Vite dev server** on port `5173`, which forwards `/api` to the backend on port `8000`.
- **Ported code mostly says where it came from.** Most services copied from `current/` have comments naming the original file and noting what was changed to fit Svelte. `testComposerService.js`, `pytest/fragmentsService.js` and `zephyr/zephyrService.js` do not have them yet.

## Gaps in Project

The project was completed within 300 hours, which allowed a large scope of work to be completed but leaving areas for future improvements with neccesary time allowed:

- **GUI Responsivness** - The Svelte frontend works on one full screen media display. This is because the scoped goal was to deliver an MVP that would allow network testers to use Ask CK from their own workbench at Allied Telesis. It is inferred by this that users would not be able to access the tool via the companies intranet on mobile devices. The responsiveness becomes an issue when users want to zoom display, or shrink their window.

- **Fully-Scoped Admin Panel** - The admin panel shows the database status and lint trends, and can reset the workspace LLM config, reset all sessions and restart the server. The legacy panel's "Reset current case session" was not ported: the Svelte app keeps the loaded case inside the Generator and PyTest pages, so the panel on the home page has no case to reset. Admin mode is also only a client-side switch (clicking the logo eight times), not a permission check, so it hides the controls but does not protect them.

- **Vitest / Spec / E2E UI Testing** - Vitest, Testing Library and jest-dom are set up, with spec files in `tests/` for the shared components, the Generator and PyTest steps, `PyTestPage` and the services. The Test Composer, Zephyr and home/settings components have no spec files yet. Only `tests/api/client.spec.js` and `tests/components/generator/OgCandidatePicker.spec.js` contain real tests; the other specs are `describe.todo` stubs, which Vitest reports as skipped. The Playwright specs in `tests/e2e/` are empty, and Playwright is not installed for this frontend.

- **Session Restore on Refresh** - Each case's work is saved on the server (in the `sessions` table of `ck.db`), so nothing is lost when the tool is closed: loading the case again continues where it left off. The Svelte app itself does not remember where the user was, though. A refresh lands on the current route with no case loaded, and the user picks the case again. The legacy frontend restored the open panel and selected case after a refresh (`current/shared/session-restore.js`). It used `sessionStorage`, so the restore lasted only for that tab, and a tab reopened later did not reload the case and take its lock away from a colleague. A port should keep that same limit.

---

### Contact

After the project, the developer of the Svelte frontend UI can be contacted via:

**E-Mail:** trentmorgan1996@gmail.com

**Phone:** +64 022 546 4126
