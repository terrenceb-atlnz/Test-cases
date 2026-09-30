# PLAN — ATUI restyle of the Ask CK front end, swappable with `current/`

> ## Status (read first)
>
> **Phase 0 BUILT 2026-09-30** (`9c996c1`, then the served/swap commit): `/restyle` is live and the
> Classic/ATUI swap is in both sidebars. The restart took ~30 s and did not wedge. **Awaiting:**
> Terrence's Phase 0 checklist, his review of the §7 mapping (incl. the severity note), then
> Phases 1–4.
>
> **Phase 1 BUILT 2026-09-30** after Terrence approved §7 (*"lets see how they look"*): ATUI colours,
> Inter Variable + Roboto Mono served locally, 13px body, restyle/ only. **Awaiting:** his look at it.
> Carried to Phase 2: 7 variables `current/` never defines (`--status-err`, `--status-ok`,
> `--status-info[-muted]`, `--color-danger`, `--text-muted`, `--border-color`) resolve to their
> hard-coded fallbacks, so those spots keep Classic colours until then.
>
> **Phase 2 BUILT 2026-09-30** ("carry on"): no raw colour left in `restyle/styles.css` outside its
> `:root` block; 427 px values on ATUI scales (spacing tokens, type scale, md/lg/full radius, control
> heights 24/28/36, input widths); `restyle/index.html`'s 15 inline styles moved to classes. **No
> shared-JS edit was needed:** the JS's style writes are display/opacity/progress behaviour, table
> layout widths, and 11px / 2px values already on ATUI's scale; its only colours are `var()`
> fallbacks, all now defined in `restyle/` (incl. `--status-warn`, which neither stylesheet had).
> Snapping rules: §8.
>
> **Phase 3 shell BUILT 2026-09-30 — Rail A** (Terrence: *"Rail A for now"*): 48px header (AT brand mark +
> "Ask CK", still `.sidebar-logo`; theme + Classic/ATUI swap on the right); 300px sidebar collapsing to a
> 50px rail of the six section icons (ATUI: only parents carry icons — the 21 step icons are gone in
> the restyle); a rail click expands with that section open (`restyle/rail.js`, 6 vitest specs
> against the real nav.js accordion, mutation-checked). theme.js's 🌙/☀️ and nav.js's ▸ are Carbon
> icons via CSS in the restyle — no shared-JS change. Terrence checked the shell 2026-09-30: all six
> checklist items pass (after the Collapse fix, `f600832`).
>
> **Phase 3 components BUILT 2026-09-30** — a CSS look-alike of ATUI's recreations: buttons (overlay
> hover/press, 3px glow, 30%+grayscale disabled, no press-scale; variant-less = ATUI secondary),
> cards, section headings, tables (ATUI's 40/48px rows, 24px inset, muted sentence-case headers),
> badges, status banners (ATUI Message: tinted + Carbon icon, no coloured edge), inputs/selects
> (active-accent focus glow), step pills. No modals exist in the app to restyle. The select chevron's
> data-URI grey (missed by 2a — the # is %23) is now Carbon's chevron in ATUI slate-500.
> **Awaiting:** Terrence's look — the tables are the largest density change; then Phase 4.
>
> **Phase 4 lists APPROVED 2026-09-30** — Terrence: *"i approve all W 1-18 suggestions and all icons. i
> approve the proposed order."* (§9, §10 as drafted, incl. W16 keep native dialogs and I11 HealthDot shapes.)
>
> **Phase 4a BUILT 2026-09-30** — every `[html]` row of §9/§10 in `restyle/index.html`, plus W17: all 8
> `text-transform: uppercase` declarations dropped from `restyle/styles.css` (the six W17 names, plus
> `.sidebar-section-label` and `.table th`, which later blocks already reset). Button icons: `arrow--down`
> (Choose Selected), `renew` (Refresh List / Preview, Re-render Prompts), `tools` (Fix Units) — Carbon
> 11.89.0, copied. Prose that names a renamed button follows it (e.g. *"Check My Local Agent"*, *"Save
> Changes"*); `claude → /login` became *"claude, then /login"* under I4's prose rule. `setButtonBusy`
> stashes/restores `innerHTML`, so an icon survives a busy cycle. Not touched (outside W13's list):
> *it's / you're / something's*; the `·` separators in *"1 · Assemble"* and *"If something's wrong ·"*.
> **Next: 4b** — the `[JS]` rows behind S11, scratch server first.
>
> Originally: **PLAN ONLY — nothing built.** Written 2026-09-30 at Terrence's request: *"lets make a plan for
> the restyle, but i want it to swap between current/ and restyle/ with a button that you make next
> to the day/night toggle."* The decisions in §0 are his and settled. Every "today" number in §1
> was measured on 2026-09-30. §6 lists the decisions still open. No phase starts without his go.
>
> **2026-09-30, later:** D1 and D2 answered (now S6, S7 in §0). Then D3, D5, D6 (now S8–S10);
> D3 raised a scope question about the shared JS, recorded as D9. Then D4, D7, D8, D9 answered
> (now S11–S16). **Every decision in §6 is now settled.** Phase 0 still waits on Terrence's go.

## 0. The ask and the settled decisions — Terrence, 2026-09-30

The guidance is governance's ATUI design system, at `docs/ATUI Design System/` (also the
`atui-design` skill). The restyle applies it to Ask CK.

| # | Decision |
|---|---|
| S1 | **`restyle/` has its own `index.html` + CSS + assets, and shares the JS** with `current/`. No second copy of the modules, so no feature drift in the JS while the restyle runs. |
| S2 | **`restyle/` is a sibling:** `ask-ck/frontend/ck-main/restyle/`, beside `current/` and `svelte/`, served at its own path. |
| S3 | **`/` always opens `current/`.** The restyle is opt-in each visit; the choice is not remembered. |
| S4 | **A swap button next to the day/night toggle**, in both UIs, switches between them. |
| S5 | **All four layers are in scope:** tokens/fonts/theme, hard-coded values, components, copy and icons. |
| S6 | **ATUI is not required for Ask CK** (was D1): *"Not for us, no. which is why we are scoping the restyle and making it toggleable just in case."* The restyle is exploratory; ATUI's rules guide it, they do not bind it. |
| S7 | **Phase 3 uses a CSS look-alike, not the real `at-*` web components** (was D2): *"sure"*, to the recommendation. |
| S8 | **Every change is in the restyle only** (was D3): *"all changes will only be in the restyle"*. `current/` keeps its look, copy and icons. The one sanctioned change to `current/` is the swap button he asked for. How this binds the shared JS is D9. |
| S9 | **The restyle never replaces `current/`** (was D5): *"DO NOT REPLACE CURRENT. THIS LIVES ALONGSIDE."* There is no cut-over phase; both UIs are permanent. |
| S10 | **Fonts and icons are copied into `restyle/`, not loaded from a CDN** (was D6, delegated: *"whatever you think is most efficient for a standalone server"*). The server is LAN-hosted; local files mean no internet dependency, no third-party request per page load, and the same caching as every other static file. One-time fetch: Inter Variable + Roboto Mono woff2 (fontsource, OFL) and only the Carbon icons actually used (`@carbon/icons` 16px, Apache-2.0), with the source version noted beside them. |
| S11 | **Shared JS may carry `data-ui="atui"` branches** (was D9, option a): *"sure, why not? (a)"*. Output for `current/` stays byte-identical, pinned by the existing tests plus new ones for the `atui` branch. This is how the restyle reaches the 32 inline style writes, the JS-emitted glyphs and the JS-emitted copy. |
| S12 | **Base size 13px, ATUI's** (was D4a): *"lets use recommended design choices"*. |
| S13 | **The CK face becomes the Allied Telesis brand mark** + "Ask CK" text (was D4b): *"swap it to the brand mark. Lame, but whatever."* The element keeps class `sidebar-logo`, so single-click Home and double-click admin panel (bound in `shared/main.js`) keep working with no JS change. |
| S14 | **The ATUI shell: 48px header + a sidebar that collapses to an icon rail** (was D4c, option iii). Header left: brand mark + "Ask CK"; header right: theme toggle + the swap control. Collapse is a `restyle/`-owned module. |
| S15 | **The swap control is a two-part segmented control, "Classic" / "ATUI"**, the active one highlighted (was D7, option C). In `current/` it sits under the Theme button; in `restyle/` beside the theme toggle in the header (S14). Tooltip on the inactive half: "Open the ATUI version. Your case and panel carry over." |
| S16 | **The Phase 0 restart follows the §6 D8 procedure, step 6 pre-authorised** (was D8): *"we will follow your procedure, should be noone on. restarting shouldnt interfere with anyone."* If the reload wedges, `systemctl --user restart ask-ck.service` without stopping to ask. Step 2 (the journal check) still runs. |

Not in scope: Trent's Svelte UI (`origin/userinterface`). This plan does not touch it, but the
token mapping (§3 Phase 1) and the icon registry (Phase 4) are reusable there.

## 1. Today (measured 2026-09-30)

- **Serving.** `paths.py: FRONTEND_DIR` → `current/`. `main.py` mounts it at `/static`
  (`StaticFiles`) and `root()` returns its `index.html` at `/`. A middleware sets
  `Cache-Control: no-cache` on `/static/**.js` only.
- **Module paths.** The modules import one another by **relative** path; the only absolute
  `/static/` references are four in `index.html` (`styles.css?v=33`, `shared/main.js?v=N`,
  `ckc.jpg` ×2). So a second page can load the same modules from `/static/shared/main.js` as-is.
- **The markup the JS binds to lives in `index.html`:** 186 `id=` and 90 `data-action=` today.
  A second `index.html` must keep every one of them, or shared JS breaks silently in one UI.
- **Theme.** `shared/theme.js` toggles `.dark` / `.light` on `<html>` and stores `theme` in
  `localStorage`; the button is `#theme-toggle` in the sidebar with a 🌙 / ☀️ `#theme-icon`.
  ATUI themes by `[data-theme='dark']`.
- **Styling.** One `styles.css`, 1,646 lines, 355 rules, 33 semantic variables (each defined for
  light and dark), 270 `var()` uses. **Hard-coded:** 54 hex colours outside the variable
  definitions, 575 px values, 15 inline `style=` in `index.html`, 32 style writes in the JS.
  Fonts: Inter + JetBrains Mono from Google Fonts.
- **Copy and icons (approximate greps).** ~13 "Apply", 2 "OK", 2 "can't", 8 "!" hits (some in
  code, not UI). **139 unicode glyphs used as icons** in JS/HTML: ✓ 38, → 33, ⚠ 24, ✗ 23, ↻ 5,
  ↓ 4, ⇄ 3, 🌙 2, ✕ 2, and single 🔒 ➕ ☀ ↑ ←. ATUI forbids emoji and unicode-as-icon.
- **Tests.** 25 of 32 vitest files assert on text or classes; 26 assertions pin glyphs. Four
  pytest files read `current/index.html` (e.g. `test_pt_step_labels.py`,
  `test_pt_testbox_profile_fields.py`).
- **Swapping reloads the page.** `shared/locks.js` releases a held case lock on `pagehide`;
  `shared/session-restore.js` restores the panel and loaded case from `sessionStorage`, which
  survives a same-tab navigation. So a swap = release, reload, restore, re-acquire.
- **The working tree is production.** Anything saved under `current/` is live at once; a save to
  `CK_server/*.py` restarts the server (uvicorn `--reload`), which can wedge on the agent
  long-polls. `restyle/` itself is harmless to users (S3), but **shared JS edits reach
  `current/` users immediately.**

## 2. Design

### 2.1 Layout on disk

```
ask-ck/frontend/ck-main/
├── current/          unchanged role: served at / and /static
├── restyle/          NEW — served at /restyle and /restyle/static
│   ├── index.html    same ids + data-actions as current/index.html; <html data-ui="atui">
│   ├── styles.css    the ATUI stylesheet (starts as a copy of current/styles.css)
│   ├── atui/         copied from docs/ATUI Design System/tokens/ (+ sync date noted)
│   └── assets/       ATUI logo marks as needed
└── svelte/           untouched
```

`restyle/index.html` loads **`/static/shared/main.js`** (the shared modules) and
**`/restyle/static/styles.css`** (its own look). `/static/ckc.jpg` stays shared.

### 2.2 Serving — one backend edit, one production restart

- **`restyle/` must exist before the save:** `StaticFiles` raises at startup on a missing
  directory, which would stop production from coming back.
- `RESTYLE_DIR = FRONTEND_DIR.parent / "restyle"` — in `main.py`, so the change is **one file,
  one save, one reload** (`paths.py` is the usual home for anchors; a second file risks a second
  reload).
- `main.py`: mount `/restyle/static` → `RESTYLE_DIR`; add `GET /restyle` returning its
  `index.html` (mirrors `root()`). `/` is unchanged (S3).
- If `restyle/` ever gains its own `.js`, extend the `no-cache` middleware to
  `/restyle/static/`. The plan does not need any.
- **The save restarts production.** Done once, by the procedure in §6 D8.

### 2.3 The swap button

- In **both** `index.html`s, beside the theme toggle: `#ui-toggle`, the segmented control of S15 —
  the active half is plain text, the other half a plain link (`<a href="/restyle">` in
  `current/`, `<a href="/">` in `restyle/`). Its styling in `current/styles.css` is part of the
  sanctioned change.
  **No JS** — so the only `current/` change is that one element (S8), and no shared module needs
  editing for the swap.
- A plain link navigates the **same tab**, which matters: `sessionStorage` (restore) survives it;
  a new tab would not.
- Nothing is persisted (S3). `/restyle` works if typed or bookmarked.
- Labels "Classic" / "ATUI" (S15); text only, no glyph, in both UIs.

### 2.4 One flag for the shared JS

`restyle/index.html` sets `<html data-ui="atui">`; `current/` sets nothing. Shared JS reads it only
to emit restyle-only output — styles, icons, copy — with `current/`'s output byte-identical (S11).

**Theme needs no JS change:** `shared/theme.js` already toggles `.dark` / `.light` on `<html>` in
both UIs, so `restyle/`'s copy of ATUI's tokens is re-keyed from `[data-theme='dark']` to
`.dark`. `restyle/` may also own JS modules of its own, loaded only by `restyle/index.html`, for
restyle-only behaviour — the collapsible sidebar (S14).

### 2.5 Keeping the two `index.html`s in step

Every `current/index.html` change during the restyle must be mirrored. Two mechanical helps:

1. **A parity test** (new, pytest): every `id` and every `data-action` in `current/index.html`
   exists in `restyle/index.html`, and both carry the same `main.js?v=N`. Fails loudly on drift.
2. The cache-bust convention (`?v=N`, `current/README.md` convention 4) applies to both files.

## 3. Phases

Each phase: gate green before and after; changes tried first on the **scratch server**
(`ask-ck/tools/run_scratch_server.sh --bg`, port 8123) when they touch shared JS; a **manual
checklist** for Terrence at the end (no Playwright — his preference). `current/` must look
exactly as before after every phase.

### Phase 0 — scaffold and the swap (no visual change yet)

1. Create `restyle/` with `index.html` = `current/index.html` + `data-ui="atui"` + its own
   stylesheet link; `styles.css` = a copy of `current/styles.css`.
2. Serving edit (§2.2) — **the one production restart.**
3. `#ui-toggle` in both files (plain links, §2.3). No shared-JS change.
4. The parity test (§2.5).
5. Point `test_pt_step_labels.py` / `test_pt_testbox_profile_fields.py` at both files **only if**
   they pin something the restyle will change; otherwise leave them on `current/`.

**Done when:** `/restyle` looks identical to `/`; the button swaps both ways; a loaded case, its
lock, the panel and the theme survive a swap; gate green; parity test green.

### Phase 1 — tokens, fonts, dark theme (restyle/ only)

- Import the copied ATUI tokens; map the 33 existing variables onto ATUI semantics (e.g.
  `--bg-primary` → `--token-surface-…`, `--accent-primary` → `--token-color-brand-primary`,
  `--status-*` → the `state-*` families). The full mapping table is written as the phase's first
  step and shown to Terrence before any CSS changes.
- Fonts: Inter Variable + Roboto Mono, copied into `restyle/atui/fonts/` (S10); `fonts.css`
  re-pointed at them.
- Dark theme on `.dark` (the re-keyed tokens, §2.4).
- 13px root (S12).

**Done when:** both themes render in ATUI colours and type; `current/` unchanged.

### Phase 2 — hard-coded values

- `restyle/styles.css`: the 54 raw hex → tokens; px → ATUI spacing (2/4/8/12/16/20/24/32…),
  radius (`md`/`lg`), control heights (36/28/24) and widths.
- `restyle/index.html`: its 15 inline styles → classes (restyle-only, free).
- **Shared JS — the 32 style writes:** these set styles inline, so `restyle/`'s CSS cannot reach
  them without `!important`. Under S11 each becomes a class when `data-ui="atui"` and stays the
  exact inline style otherwise, so `current/` is byte-identical.

**Done when:** no raw hex outside token definitions in `restyle/styles.css`; `current/` pixel-
same by Terrence's eye on the checklist.

### Phase 3 — components

**The shell first (S13, S14):** the 48px header with the brand mark (still `.sidebar-logo`), the
theme toggle and the swap control; the sidebar below it, collapsing to an icon rail via a
`restyle/`-owned module. All 21 nav items carry an inline SVG today, so each gets a Carbon icon
(counted into S10's fetch). **To show Terrence before building it:** 21 icons in a 50px rail is
busy — the PyTest Creator alone is 7 step items — so the collapsed rail's content (every item,
or one icon per tool section expanding on hover) is a mock-up for him to pick from.

Then, in ATUI's terms: buttons (`.btn` variants → ATUI's types × sizes), the sidebar and
nav items, cards/panels, tables, the PyTest Creator's 7-step stepper, badges and status banners,
modals/confirmations, inputs and selects, the LLM-busy button states.

The method is a **CSS look-alike** (S7): our own markup, styled to match ATUI's components. The
reason: the shared JS (S1) renders ~45 buttons and every candidate table as HTML strings, so real
`at-*` components in JS output would need per-UI render branches.

**Done when:** each component matches ATUI's recreation in `docs/ATUI Design System/components/`
by Terrence's review; hover/press/focus/disabled per ATUI's rules.

### Phase 4 — copy and icons

- **Icons:** the 139 glyphs are emitted by shared JS and `index.html`. In `restyle/index.html`
  they become Carbon icons directly. For the JS-emitted ones (S11): an
  `icon(name)` helper returning today's glyph when `data-ui` is absent — `current/` byte-identical,
  the 26 glyph assertions still pass — and a copied Carbon SVG when it is `atui`, S10).
- The theme icon (🌙/☀️) and any glyph in `restyle/index.html` become Carbon icons there.
- **Copy:** the locked verb rules ("Save changes" not "Apply"/"OK", "Cannot", Title Case CTAs,
  named confirmations, None / Unknown / No data). A hit list with each proposed rewrite goes to
  Terrence first. They apply to the restyle only (S8); JS-emitted strings branch on `data-ui` (S11).

**Done when:** no glyph-as-icon in the ATUI UI; every agreed rewrite in; gate green.

### Phase 5 — none

There is no cut-over: the restyle lives alongside `current/` permanently (S9).

## 4. Risks

| Risk | Mitigation |
|---|---|
| Shared-JS edits (Phases 0, 2, 4) change `current/` for live users | scratch server first; output for `current/` kept identical; checklist per phase |
| The two `index.html`s drift | parity test (§2.5) |
| The serving edit wedges production on restart | one file, one save, `restyle/` created first; the D8 procedure |
| A swap loses a case lock to another user in the release→re-acquire gap | the gap is one page load; a Phase 0 checklist item confirms the lock comes back |
| Governance files and our copy diverge | copy is dated from `github.md`'s last-sync; re-sync is a deliberate step, never automatic |

## 5. Test and verification approach

- The gate (`./ask-ck/tools/run_tests.sh`) before and after each phase.
- New automated checks, each named in its phase: the parity test (Phase 0), `atui`-branch icon
  tests (Phase 4). No Playwright.
- A manual checklist per phase for Terrence, in both themes and both UIs.

## 6. Open decisions — Terrence's

| # | Question | Notes / recommendation |
|---|---|---|
| ~~D1~~ | ~~Does governance require ATUI for internal tools?~~ | **Answered 2026-09-30 → S6: no.** |
| ~~D2~~ | ~~Phase 3 method: CSS look-alike, or the real `at-*` web components?~~ | **Answered 2026-09-30 → S7: look-alike.** |
| ~~D3~~ | ~~Copy rewrites: both UIs, or restyle only?~~ | **Answered 2026-09-30 → S8: restyle only.** |
| ~~D4~~ | ~~13px root; the CK face; the shell layout~~ | **Answered 2026-09-30 → S12, S13, S14.** |
| ~~D5~~ | ~~End state: replace `current/`?~~ | **Answered 2026-09-30 → S9: never; both stay.** |
| ~~D6~~ | ~~Fonts and icons: jsDelivr or copied?~~ | **Answered 2026-09-30 → S10: copied (delegated).** |
| ~~D7~~ | ~~The swap button~~ | **Answered 2026-09-30 → S15: segmented "Classic" / "ATUI".** |
| ~~D8~~ | ~~When and how to make the Phase 0 restart~~ | **Answered 2026-09-30 → S16; procedure below.** |
| ~~D9~~ | ~~May shared JS branch on `data-ui`?~~ | **Answered 2026-09-30 → S11: yes, option (a).** |

### The Phase 0 restart procedure (S16)

1. Create `restyle/` and its `index.html` first — no effect on anyone, and `StaticFiles` fails
   startup on a missing directory.
2. Check the journal for sessions active in the last 2 minutes
   (`journalctl --user -u ask-ck.service --since -2m | grep -oE 'session=sess-[a-z0-9]+' | sort -u`)
   and tell Terrence who is on.
3. Terrence says go.
4. Save `main.py` once (one file, one reload).
5. Within 30 s: `/health` (`is_permanent_db: true`), then load `/` and `/restyle`.
6. No answer after ~60 s → `systemctl --user restart ask-ck.service` (pre-authorised, S16).

What a reload costs users: a few seconds' outage; in-flight LLM calls (Generate / Fix / Review)
are killed; case locks (in memory) are dropped — whether open tabs re-take them is a Phase 0
checklist item; `ck.db` sessions survive.

## 7. Phase 1 — the variable mapping (DRAFT, for Terrence before any CSS changes; severity settled)

`restyle/styles.css` keeps today's 35 variable *names* — so its 270 `var()` uses need no edit —
and re-points each at an ATUI token. Both themes come from ATUI (`restyle/atui/atui-tokens.css`:
light on `:root`, dark on `.dark`). Where ATUI has no direct token the value is built the way
its readme says (hover = an overlay, never a new colour; focus = a 3px active-accent ring at 50%).

| Today (`current/`) | Used for | → ATUI |
|---|---|---|
| `--bg-primary` | page background | `--token-surface-background` |
| `--bg-secondary` | cards, panels | `--token-surface-foreground` (white in light) |
| `--bg-tertiary` | inputs, recessed areas | `--token-surface-1` |
| `--bg-sidebar` | sidebar | `--token-sidebar-background` |
| `--bg-elevated` | modals, menus | `--token-surface-foreground` (+ `--token-shadow-2`) |
| `--bg-hover` | hover fill | `color-mix(in srgb, var(--token-surface-overlay) 10%, transparent)` |
| `--bg-active` | selected item | `--token-state-active-background` |
| `--text-primary` | body text | `--token-text-foreground` |
| `--text-secondary` | supporting text | `--token-text-secondary` |
| `--text-tertiary` | hints, captions | `--token-text-tertiary` |
| `--text-inverse` | text on blue fills | `--token-color-brand-primary-foreground` |
| `--border-default` | hairlines | `--token-border-muted` (ATUI: hairlines everywhere are `border-muted`) |
| `--border-subtle` | faint dividers | `--token-border-muted` |
| `--border-strong` | emphasised edges | `--token-border-default` |
| `--accent-primary` | primary buttons, links | `--token-color-brand-primary` (#2979ff) |
| `--accent-hover` | primary hover | `color-mix(in srgb, var(--token-color-brand-primary) 70%, black)` (ATUI: 30% darkening) |
| `--accent-muted` | tinted accent fills | `--token-state-active-background` |
| `--accent-text` | accent-coloured text | `--token-text-active` |
| `--status-critical` / `-muted` | severity: critical | `--token-state-error-accent` / `--token-state-error-background` |
| `--status-high` / `-muted` | severity: high | `--token-state-warning-accent` / `--token-state-warning-background` |
| `--status-medium` / `-muted` | severity: medium | `--chart-alert-2` (ATUI's chart amber) / its 15% tint over `--token-surface-foreground` — option (b) |
| `--status-low` / `-muted` | severity: low | `--token-text-muted` / `--token-surface-1` |
| `--status-success` / `-muted` | pass, done | `--token-state-success-accent` / `--token-state-success-background` |
| `--focus-ring` | focus outline | `color-mix(in srgb, var(--token-state-active-accent) 50%, transparent)`, 3px |
| `--overlay` | modal backdrop | `rgb(0 0 0 / 20%)` (ATUI: black at 20%) |
| `--shadow-sm` / `-md` / `-lg` | elevation | `--token-shadow-1` / `-2` / `-3` |
| `--font-sans` | UI text | `--token-font-family-base` (Inter Variable) |
| `--font-mono` | code, IPs, CLI | `--token-font-family-mono` (Roboto Mono Variable) |

Plus: `restyle/atui/fonts.css`, `atui-tokens.css` and `base.css` imported at the top; body text
13px (S12), replacing today's 14px; the Google Fonts `<link>` dropped from `restyle/index.html`.

**Note — severity has one level more than ATUI.** Today has critical / high / medium / low (35
uses); ATUI's states are error / warning / success / info, and its alert chart palette is
green / amber / red / grey. Options: (a) medium shares high's amber (loses the distinction);
(b) medium = ATUI's chart amber `--chart-alert-2`, high = the warning accent (keeps four
levels, two of them close in hue); (c) medium = `--token-state-info-accent` (blue — keeps it
distinct but blue reads as "info", not severity). **Terrence, 2026-09-30: (b).** The `-muted`
tint is my construction (ATUI defines no background for chart colours) — shown in the Phase 1
checklist so it can be judged by eye.

## 8. Phase 2 — the snapping rules actually applied (2026-09-30)

Ties snap **down**, toward ATUI's density. `restyle/` only; the specimen CSS and `:root` untouched.

| What | Rule | Count |
|---|---|---|
| padding / margin / gap | nearest of 2/4/8/12/16/20/24/32/40/48 → `var(--token-space-N)`; &lt;2 or &gt;48 left (hairlines, layout) | 255 |
| font-size | 9–11 → xs · 12–13 → sm · 14 → body · 15 → h5 · 16 → h3 · 20 → h2 · 24 → h1 | 106 |
| border-radius | 3–4 → md · 6–8 → lg · ≥20 → 9999px | 48 |
| height / min-height, 24–40 | nearest of 24 / 28 / 36 | 10 |
| input-width helpers | `.form-input-small` → input-sm, `.form-input-search` → input-lg | 2 |
| left alone | border widths, shadows, layout widths/heights, positions — the sidebar width is Phase 3's | — |

Biggest visible shifts: 6px gaps/paddings → 4 (39), 10 → 8 (23), 13px text → 12 (16), 14px → 13 (10).

## 9. Phase 4 — the wording list (APPROVED 2026-09-30, all rows; restyle only, S8)

Audited 2026-09-30 against ATUI's LOCKED content rules (`docs/ATUI Design System/readme.md`, Content
fundamentals). **[html]** = `restyle/index.html`, free to change. **[JS]** = emitted by the shared JS, so
it needs a `data-ui="atui"` branch (S11) and Classic's output stays byte-identical. No exclamation
marks were found. Most `confirm()` texts already name the object and the consequence.

| # | Today | Proposed | Where | Rule |
|---|---|---|---|---|
| W1 | Apply / Login | Save Changes | html (LLM Configure) | *Save changes* commits, never Apply |
| W2 | Apply Step Edits | Save Changes | JS generator.js | same |
| W3 | Apply this fix | Save Fix | JS pytest.js (held fix) | same |
| W4 | Apply all held fixes | Save All Held Fixes | html (Generate) | same |
| W5 | "Apply: …" / "Apply all: …" status lines | "Save: …" / "Save all: …" | JS pytest.js | same |
| W6 | OK, refresh | Refresh Page | JS version.js (stale-tab banner) | never OK |
| W7 | dismiss | Close | JS pytest.js (unit errors) | *Close* dismisses a view |
| W8 | ✕ (sequence row) | Remove | JS pytest.js | *Remove* takes out of a set |
| W9 | ✕ (testbox row) | Delete | JS pytest.js | *Delete* destroys |
| W10 | + Add step (×2) · + Add setup · ➕ Add new testbox… | New Step · New Setup · New Testbox… | JS + html | CTA to make new = *New {Noun}* |
| W11 | Clear selected contents (×3) | Clear Selected | html (Generator 2–4) | *Clear* empties; Title Case |
| W12 | prose: "for you to Apply or Discard" · "until you Apply a new one" · "Apply / Login sets the LLM" | "…to Save or Discard" · "until you save a new one" · "Save Changes sets the LLM" | html + JS | follows W1/W3 |
| W13 | can't (×2) · don't (×3) · wasn't · doesn't | cannot · do not · was not · does not | html + JS (7 sites) | "Cannot" for blocks; "Do not" for advice |
| W14 | ~35 button labels in sentence/lower case (Check my local agent, Health check, Choose selected, Refresh list, Generate all units (LLM), Re-render prompts, Assemble only, Confirm step 5, Fix units (LLM), Fix whole script (LLM), Re-chunk from script, Prune library…, Clear form, view, edit, check, re-run, Take over, Copy prompt, Copy response, Run anyway, Fix this unit (LLM), Refresh (no send), Choose ticked for sequence step N, Remove ticked from sequence step, …) | Title Case each (Check My Local Agent, Health Check, …, View, Edit, Check, Re-run, …) | html + JS | buttons are Title Case |
| W15 | confirm: Delete testbox "{name}"? | Delete testbox {name}? This permanently deletes its connection details and setups. This cannot be undone. | JS pytest.js | a confirmation names object **and** consequence |
| W16 | native `confirm()` / `alert()` dialogs (28 alerts, 7 confirms) | keep native; reword only per W12–W15 | JS | ATUI wants `at-dialog`; building an in-page dialog is a shared-JS feature for both UIs — **recommend keep native** |
| W17 | CSS `text-transform: uppercase` on .splash-tag, .page-eyebrow, .pt-step-sub, .pt-unit-frame-label, .provenance-label, .chosen-heading ("CANDIDATES — TICK ROWS…") | remove; text shows as written | restyle CSS | never force case with CSS |
| W18 | glyphs inside prose: "Each step shows a ✓ covered / ✗ gap status" · "Drag ⠿ to reorder." · "(⏸)" · "units ⇄ script" · "LLM → Configure" (×3) · "Confirm Objectives → Step 6" · "Save & Confirm → Step 6" | "Each step shows whether it is covered or has a gap." · "Drag a row to reorder." · "(held)" · "units and script" · "LLM, Configure" · "Confirm Objectives" · "Save and Confirm" | html + JS | no unicode-as-icon |

## 10. Phase 4 — the icon map (APPROVED 2026-09-30, all rows and the 4a/4b order)

Every glyph used as an icon, today → the Carbon icon (copied locally, S10). Counts exclude the specimen.
In `restyle/index.html` the swap is direct; for JS-emitted glyphs an `icon(name)` helper returns today's
glyph when `data-ui` is absent (Classic byte-identical) and the Carbon icon when it is `atui` (S11).
9 JS sites set a glyph through `textContent` and move to markup in the ATUI branch.

| # | Glyph (count) | Means | → Carbon |
|---|---|---|---|
| I1 | ✓ (32) | confirmed, covered, done | `checkmark` (badges: `checkmark--filled`) |
| I2 | ✗ (18) | gap, failed, high severity | `close` (failed/gap); high severity → I11 |
| I3 | ⚠ (24) | stale, warning, refused | `warning--alt--filled` |
| I4 | → (15) | "next step" in buttons; a path in prose | buttons: `arrow--right`; prose: W18 |
| I5 | ⏸ (7) | fix held for approval | `pause--filled` |
| I6 | ↻ (5) | refresh, re-render | `renew` |
| I7 | ↓ (4) · ↑ (1) | choose into / remove from the chosen list | `arrow--down` · `arrow--up` |
| I8 | ⏹ (3) | stopped | `stop--filled--alt` (ATUI `stop`) |
| I9 | ‹ › (3 + 3) | Prev / Next | `chevron--left` · `chevron--right` |
| I10 | ⏳ (3) | pinging / rendering / seat-limit pill | busy text → the existing `.ck-spinner`; limit pill → `time` |
| I11 | ✗ △ · (review severity) | high / medium / low | ATUI HealthDot shapes: diamond / triangle / circle (not colour-only) |
| I12 | ⤺ (2) | Fix units | `tools` |
| I13 | ⇄ (2) | units ⇄ script | text (W18) |
| I14 | ⠿ (2) | drag handle | `draggable` |
| I15 | ✕ (2) | remove row / delete testbox | `close` / `trash-can` (with W8/W9 labels) |
| I16 | ➕ (1) | inside a `<select>` option | text only (W10) — an option cannot hold an icon |
| I17 | 🔒 (1) | case lock banner | `locked` |
| — | 🌙 ☀ ▸ | theme, accordion caret | done in Phase 3 (CSS) |

**Proposed order:** 4a = everything `[html]` + W17 (restyle files only, no JS); 4b = the `[JS]` rows
behind S11 branches, trialled on the scratch server first because the shared JS is live for Classic.

