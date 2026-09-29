at-table / at-search-table — data grid with sort, selection, row menu, pagination and cell renderers.

```jsx
<TableActions search={q} onSearch={setQ} />
<Table columns={[{field:"name",header:"Name"},{field:"status",header:"Status",cell:"status"}]} rows={rows} />
```

Cells: text, mono, titleSubtitle, textIcon, badge, status, healthDot, colorStatus, chips, progress, relative, badgeCount, toggle. Also exports TablePagination, TableActions, ColumnManager, TableFilterMenu.
