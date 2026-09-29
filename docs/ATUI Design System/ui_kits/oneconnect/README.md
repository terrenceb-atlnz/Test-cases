# OneConnect UI kit

Click-through recreation of the OneConnect prototype (`examples/oneconnect` in atui-components), composed from this design system's components.

- `Shell.jsx` — header (OneConnect logo, global search, customer context switcher, Help, AI Network Assistant, inbox, account menu with theme toggle) and the collapsible left sidebar.
- `Sites.jsx` — Sites list: breadcrumb, header with `New Site`, clickable cohort count tiles that filter the table, search table with row menu; site **peek** side panel; delete confirmation dialog (blocked vs allowed); New Site side-panel form.
- `Pages.jsx` — Dashboard widget grid (trend, breakdown, bar, donut, gauge), Events log with tabs + severity filter, AI assistant right rail.

Other workspaces render a disclaimer placeholder — they exist in the source but are not recreated here.
