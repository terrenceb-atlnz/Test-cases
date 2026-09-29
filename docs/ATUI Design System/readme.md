# ATUI Design System (Allied Telesis)

ATUI is the Allied Telesis component library and design language behind its network-management products — chiefly **OneConnect** (cloud network management for partners, providers and customers), plus Vista Manager and on-device web GUIs. It ships as Stencil web components (`at-*` tags) with Angular, React and Vue wrappers, styled with Tailwind v4 over a `--token-*` CSS-variable layer that supports live light/dark theming.

This project recreates that system for design work: tokens, fonts, logos, React recreations of every component family, specimen cards and a OneConnect UI kit.

## Sources

- GitHub: **https://github.com/alliedtelesis-labs-nz/atui-components** (branch `main`). Explore it further — it is far richer than this summary.
  - `atui-components-stencil/src/directives.scss` — **source of truth for CSS variables** (light `:root` + `[data-theme='dark']`). Our `tokens/atui-tokens.css` is synced to it.
  - `atui-components-stencil/tailwind.css` — the Tailwind `@theme` that maps tokens to utilities (`bg-surface-1`, `rounded-card`, `p-16`).
  - `atui-components-stencil/src/components/**` — the 100+ component sources (read for exact classes).
  - `docs/ux-patterns/` — the UX pattern library (glossary, confirmations, forms, tables, modal workflows, status feedback). LOCKED rules.
  - `atui-skills/` — the team's agent skills (style guide, component selection, feature build, audit).
  - `examples/oneconnect/` — the hi-fi OneConnect prototype the UI kit is based on.
- Storybook: https://alliedtelesis-labs-nz.github.io/atui-components-docs/storybook/
- OneConnect prototype: https://alliedtelesis-labs-nz.github.io/atui-components-docs/demo-oneconnect/
- Ignored per brief: `atui-typography` and `atui-design-tokens` dist outputs.

## Index

- `styles.css` — entry point (imports only) → `tokens/fonts.css`, `tokens/atui-tokens.css`, `tokens/base.css`, `tokens/richtext.css`
- `tokens/` — fonts, all tokens (primitives → semantic → component → chart palettes, light + dark), base element styles + plain-table skin, `.richtext`
- `assets/` — `at-logo.svg` (Allied Telesis gradient mark), `atui-sm.svg` / `atui-lg.svg` (ATUI lockups), `oneconnect-logo-light/dark.svg`, `ai-network-assistant-logo.svg`
- `components/<group>/` — React recreations (`.jsx` + `.d.ts` + `.prompt.md`, one `*.card.html` per group)
- `guidelines/` — foundation specimen cards (colour, type, spacing, radius, shadow, motion, brand)
- `ui_kits/oneconnect/` — interactive OneConnect recreation (`index.html`, `Shell.jsx`, `Sites.jsx`, `Pages.jsx`)
- `thumbnail.html`, `SKILL.md`, `github.md`

## Components

Every family in the Stencil catalogue is represented. Names map 1:1 to `at-*` tags.

- **actions/** — Button (`at-button`, 9 types × 3 sizes), ReloadButton
- **core/** — Icon (`at-icon`, Carbon registry incl. all `ATUI_ICONS`)
- **feedback/** — Badge, HealthDot, Loading, Message, Tooltip, ProgressBar, StatusBar, Toast + Toaster, Avatar, Placeholder, RelativeTime
- **forms/** — FormLabel (+FieldHeader), Input (+InputShell), Checkbox, CheckboxGroup, Radio, RadioGroup, ToggleSwitch, ButtonGroup, ButtonSwitch, Search, Textarea, InputNumeric, InputRange, InputDate, InputTime, Select, SelectOption, MultiSelect, ChipList, TimeRange, SrcDest, ControlGroup
- **layout/** — Card, ListItem, Accordion + AccordionItem, Header, Layout, Dashboard, Resizable
- **navigation/** — Tabs, Sidebar + SidebarMenuItem + SidebarSubmenu, Breadcrumb, Tree, ListSelector + ListSelectorItem, Stepper
- **overlays/** — Menu + MenuItem, Dialog, SidePanel
- **data/** — Table (at-table / at-search-table / at-static-table) with Cells (text, mono, titleSubtitle, textIcon, badge, status, healthDot, colorStatus, chips, progress, relative, badgeCount, toggle), TablePagination, TableActions, ColumnManager, TableFilterMenu
- **charts/** — ChartBarLine, ChartDonut, ChartGauge, ChartSparkline, ChartTrend, ChartBreakdown
- **prompt/** — PromptContainer, PromptThread, PromptMessage, PromptInput

**Intentional additions:** `FieldHeader` / `InputShell` (shared label + bordered-shell helpers so every control matches `at-input`), `Toaster` as a declarative wrapper for the imperative `at-toaster`, `Cells` map standing in for cell-renderer components. Charts are lightweight SVG recreations (the originals wrap ECharts) — palette and chrome tokens are exact, geometry is simplified.

## CONTENT FUNDAMENTALS

The copy is enterprise, plain and exact — written for network admins who need to know precisely what an action does. Rules come from `docs/ux-patterns/glossary.md` (LOCKED) and `confirmations.md`.

- **Voice:** third-person system voice and second person for the reader ("You're not assigned to this site. Contact your Organisation admin to request access."). No "we", no marketing, no exclamation marks, **no emoji**.
- **Casing:** buttons/CTAs in Title Case (`New Site`, `Open Full Page`, `Clear Filter`, `Delete Site`); headings, labels, messages in sentence case. Never force case with CSS — casing belongs to the text (translations decide). Identifiers keep exact casing (`AT-x550-hq-01`).
- **Verb vocabulary (locked):** *Delete* destroys; *Remove* takes out of a set; *Discard* throws away unsaved edits; *Cancel* backs out; *Close* dismisses a view; *Clear* empties; *Reset* returns defaults; *Save changes* commits (never Apply/OK); *Create* makes new, *Add* puts existing into a set; CTA form is `New {Noun}`, commit is `Create {Noun}`.
- **Negatives:** "Cannot" (never "Can't") for system blocks; "Do not" for advice.
- **Confirmations name the object and the consequence** — never a generic "Are you sure?": `Delete Auckland HQ?` / "This will permanently delete Auckland HQ. This can't be undone." When blocked, say why and offer the way forward, and omit the destructive button rather than disabling it: "3 device(s) are still assigned to this site. Reassign every device to another site before deleting."
- **Honest empty states:** *None* (known empty) ≠ *Unknown* (never measured) ≠ *No data* (measured, nothing returned). Zero-state offers a create CTA ("No sites yet — Create your first site to start tracking device and health status"); a search miss offers none ("No sites match this search.").
- **People:** "User" (not member/holder). Permission levels: `No access` / `Read-only` / `Read & write`.
- **Units in labels**, in parentheses: `Timeout (seconds)`, `Threshold (%)`.

## VISUAL FOUNDATIONS

- **Overall vibe:** dense, calm, utilitarian operations UI. Neutral grey surfaces, one electric blue accent (`--token-color-brand-primary` = blue A400 `#2979ff`), status colour used only to mean status. Flat — hairlines over shadows.
- **Type:** Inter Variable everywhere on a **13px root** (`rem` = 13px). Body 1rem/400, headings 500 (h1 22px → h5 14px), labels xs 11px/500, sm 12px for supporting text, display `xl` 3rem for metric values. Roboto Mono for IPs/MACs/config. Line-height 140% (richtext 155%). No uppercase pseudo-headings.
- **Colour:** semantic tokens only — text (foreground/secondary/tertiary/muted/disabled/active/inv), surfaces (background `neutral-50`, foreground white, 0/1/2 recessed), state families (success/warning/error/info/active/disabled, each with foreground/background/-inv/accent), feedback fills (50% mix). Chart palettes by meaning: categorical, sequential, alert, device-status, onboarding-status, events. Full dark theme under `[data-theme='dark']`.
- **Spacing:** literal px scale 2/4/8/12/16/20/24/32/40/48… Rhythm: 4/8 inside controls, 8/12 between related items, 16 page and card padding, 24 table cell inset.
- **Sizing:** controls 36px (lg) / 28 (md) / 24 (sm); navbar 48; page header 72; sidebar 300 (collapsed 50); menu 280; widths `input-sm/md/lg` 180/220/260 for controls, `panel-xs…xl` 320–700 for containers — never mixed.
- **Corners:** `md` 0.3rem (~4px) buttons/inputs/badges/menu items; `lg` 0.46rem (~6px) cards, menus, messages; full round for toggles, progress, avatars.
- **Cards:** white `surface-foreground`, 1px `border-muted` hairline, `lg` radius, no shadow by default; header p16 with h4/500 title + sm muted subtitle; content `8px 16px 16px`.
- **Borders:** `border-muted` (grey-300) hairlines everywhere (cards, dividers, table rows, sidebar edge); inputs, toggles and segmented controls use `border-muted` too.
- **Shadows:** `shadow-1` subtle, `shadow-2` menus/tooltips, `shadow-3` dialogs, `shadow-md` side panels. Nothing heavier.
- **Hover:** a translucent overlay, never a new colour — `surface-overlay` at 10% on secondary/menu/options (7% on sidebar items), 30% darkening over primary/destructive fills, `active-accent` at 10% on outline/text variants. Links underline on hover. Rows go to `surface-background`.
- **Press:** deeper overlay (primary → accent 70%, outline → accent 20%). No scale/shrink.
- **Focus:** 3px ring of `active-accent` at 50% (`ring-active-glow`); inputs also switch border to `active-accent`; error fields use an error glow.
- **Selected state:** `state-active-background` (sky-100) fill + `state-active-foreground` text for options, checkbox/radio rows, segmented buttons, sidebar items. Tabs use a 2px `active-accent` underline that slides (150ms).
- **Disabled:** opacity 0.3 + grayscale on buttons; `surface-1` fill, no border for inputs.
- **Motion:** 150ms ease-in-out for colour/hover; 300ms for side panels and sidebar width; fades 0.15–0.2s; dialog/toast rise 20px (`animInUp`). No bounce, no parallax. Theme swap disables transitions.
- **Transparency & blur:** only on sticky side-panel headers/footers and sticky card headers (surface at 80% + `backdrop-blur`). Dialog backdrop is black at 20%.
- **Backgrounds & imagery:** none — no gradients, textures, illustrations or photography in product UI. The only gradient is inside the Allied Telesis logo mark.
- **Layout:** fixed 48px header, left sidebar (push, collapsible to icons), content region, optional right rail (AI assistant / help, resizable). Detail opens as a non-modal right **peek** side panel over the list; confirmations are `at-dialog` wrapping an `at-card`.

## ICONOGRAPHY

- **IBM Carbon Icons** via `<at-icon name="…">` (migrated from Material Icons, now deprecated). 16px default, `fill: currentColor` so icons take the surrounding text colour. Sidebar items use 22px.
- Names are snake_case registry keys (`add`, `chevron_down`, `overflow_menu`, `warning`, `info_filled`, `trend_up`…). The built-in `ATUI_ICONS` set is mirrored in `components/core/Icon.jsx` → `ATUI_ICON_PATHS`, with app icons added.
- Our `Icon` loads the real `@carbon/icons` ES modules from jsDelivr (`@carbon/icons@11/es/<path>/16.js`) and renders the SVG exactly as `at-icon` does — no substitution. Use `carbon="…"` for any Carbon path not in the registry.
- Icons carry meaning, not decoration: no icons on page/section headers, card titles or sidebar sub-items. `Message` preset types render their own icon.
- Health uses dedicated shape-coded glyphs (`HealthDot`: circle / triangle / diamond) so status is not colour-only.
- No emoji, no unicode-as-icon. Brand marks: `assets/at-logo.svg` (24px in the header, also favicon), OneConnect wordmark SVGs, AI assistant mark (used as a CSS mask so it recolours).
