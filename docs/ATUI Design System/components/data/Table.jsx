import React from "react";
import { Icon } from "../core/Icon.jsx";
import { Button } from "../actions/Button.jsx";
import { Badge } from "../feedback/Badge.jsx";
import { HealthDot } from "../feedback/HealthDot.jsx";
import { ProgressBar } from "../feedback/ProgressBar.jsx";
import { RelativeTime } from "../feedback/RelativeTime.jsx";
import { Checkbox } from "../forms/Checkbox.jsx";
import { ToggleSwitch } from "../forms/ToggleSwitch.jsx";
import { Search } from "../forms/Search.jsx";
import { Select } from "../forms/Select.jsx";
import { ChipList } from "../forms/ChipList.jsx";
import { Menu } from "../overlays/Menu.jsx";
import { Placeholder } from "../feedback/Placeholder.jsx";

// Cell renderers — mirror table-components/cell-components/*
export const Cells = {
  text: (v) => <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{v}</span>,
  mono: (v) => <span style={{ fontFamily: "var(--token-font-family-mono)", fontSize: "var(--token-font-size-sm)" }}>{v}</span>,
  titleSubtitle: (v) => <span style={{ display: "flex", flexDirection: "column", lineHeight: 1.3 }}><span>{v.title}</span><span style={{ color: "var(--token-text-muted)", fontSize: "var(--token-font-size-sm)" }}>{v.subtitle}</span></span>,
  textIcon: (v) => <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}><Icon name={v.icon} />{v.text}</span>,
  badge: (v) => <Badge label={v.label} type={v.type} />,
  status: (v) => <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}><HealthDot status={v.status} size="sm" />{v.label}</span>,
  healthDot: (v) => <HealthDot status={v} size="sm" />,
  colorStatus: (v) => <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}><span style={{ width: 8, height: 8, borderRadius: 999, background: v.color }}></span>{v.label}</span>,
  chips: (v) => <ChipList chips={v} removable={false} />,
  progress: (v) => <ProgressBar percentage={v} style={{ width: 120 }} label_after={<span style={{ fontSize: "var(--token-font-size-xs)", width: 32 }}>{v}%</span>} />,
  relative: (v) => <RelativeTime date={v} />,
  badgeCount: (v) => <Badge label={String(v)} rounded type={v ? "info" : "disabled"} />,
  toggle: (v, row, set) => <ToggleSwitch value={v} show_label={false} label="Toggle" onChange={set} style={{ padding: 0 }} />,
};

/** at-table — data grid (ag-grid skin: 40px header, 48px rows, 24px cell padding, hairline rows). */
export function Table({ columns = [], rows = [], selectable, onRowClick, row_actions, sort: sortInit, empty, page_size = 10, paginate = true, style }) {
  const [sel, setSel] = React.useState([]);
  const [sort, setSort] = React.useState(sortInit || null);
  const [page, setPage] = React.useState(1);
  const [ps, setPs] = React.useState(page_size);
  const [hov, setHov] = React.useState(-1);
  let data = rows;
  if (sort) { const c = columns.find((x) => x.field === sort.field); data = [...rows].sort((a, b) => { const x = c.sortValue ? c.sortValue(a) : a[sort.field], y = c.sortValue ? c.sortValue(b) : b[sort.field]; return (x > y ? 1 : x < y ? -1 : 0) * (sort.dir === "asc" ? 1 : -1); }); }
  const pages = Math.max(1, Math.ceil(data.length / ps));
  const view = paginate ? data.slice((page - 1) * ps, page * ps) : data;
  const all = view.length > 0 && view.every((r) => sel.includes(r.id));
  const th = { height: 40, padding: "0 24px", textAlign: "left", fontWeight: "var(--token-font-weight-med)", color: "var(--token-text-muted)", whiteSpace: "nowrap", background: "var(--token-surface-foreground)", position: "sticky", top: 0, zIndex: 1, borderBottom: "1px solid var(--token-border-muted)" };
  return (
    <div style={{ display: "flex", flexDirection: "column", ...style }}>
      <div style={{ overflow: "auto", background: "var(--token-surface-foreground)" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--token-font-size-base)" }}>
          <thead><tr>
            {selectable && <th style={{ ...th, width: 40, padding: "0 0 0 16px" }}><input type="checkbox" checked={all} onChange={() => setSel(all ? [] : view.map((r) => r.id))} style={{ accentColor: "var(--token-state-active-foreground)", width: 16, height: 16 }} /></th>}
            {columns.map((c) => (
              <th key={c.field} style={{ ...th, width: c.width, cursor: c.sortable !== false ? "pointer" : "default" }} onClick={() => c.sortable !== false && setSort(sort && sort.field === c.field ? { field: c.field, dir: sort.dir === "asc" ? "desc" : "asc" } : { field: c.field, dir: "asc" })}>
                <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>{c.header}{sort && sort.field === c.field && <Icon name={sort.dir === "asc" ? "caret_up" : "caret_down"} size={14} />}</span>
              </th>
            ))}
            {row_actions && <th style={{ ...th, width: 48 }}></th>}
          </tr></thead>
          <tbody>
            {view.map((r, i) => (
              <tr key={r.id ?? i} onMouseEnter={() => setHov(i)} onMouseLeave={() => setHov(-1)} onClick={() => onRowClick && onRowClick(r)}
                style={{ height: 48, borderBottom: "1px solid var(--token-border-muted)", cursor: onRowClick ? "pointer" : "default", transition: "background-color 150ms",
                  background: sel.includes(r.id) ? "color-mix(in srgb, var(--token-state-active-accent) 12%, transparent)" : hov === i ? "var(--token-surface-background)" : "transparent" }}>
                {selectable && <td style={{ padding: "0 0 0 16px" }} onClick={(e) => e.stopPropagation()}><input type="checkbox" checked={sel.includes(r.id)} onChange={() => setSel(sel.includes(r.id) ? sel.filter((x) => x !== r.id) : [...sel, r.id])} style={{ accentColor: "var(--token-state-active-foreground)", width: 16, height: 16 }} /></td>}
                {columns.map((c) => <td key={c.field} style={{ padding: "0 24px", maxWidth: c.width || 320, color: "var(--token-text-foreground)" }}>{(c.cell ? (typeof c.cell === "string" ? Cells[c.cell] : c.cell) : Cells.text)(r[c.field], r)}</td>)}
                {row_actions && <td style={{ padding: "0 8px" }} onClick={(e) => e.stopPropagation()}><Menu align="end" trigger={<Button size="md" type="secondaryText" icon="overflow_menu" />} items={row_actions(r)} /></td>}
              </tr>
            ))}
          </tbody>
        </table>
        {view.length === 0 && (empty || <Placeholder size="sm" placeholder_title="No results" content="Try a different search or clear the filters." />)}
      </div>
      {paginate && data.length > 0 && <TablePagination current_page={page} num_pages={pages} page_size={ps} onChange={setPage} onPageSizeChange={(n) => { setPs(n); setPage(1); }} />}
    </div>
  );
}

/** at-table-pagination — page size select + first/prev/next/last. */
export function TablePagination({ current_page = 1, num_pages = 1, page_size = 20, page_size_options = [5, 10, 20, 50, 100], onChange, onPageSizeChange }) {
  return (
    <div style={{ marginTop: 8, display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 8 }}>
      <span>Page Size:</span>
      <Select width={80} options={page_size_options.map((v) => ({ value: v, label: String(v) }))} value={page_size} onChange={(v) => onPageSizeChange && onPageSizeChange(v)} />
      <Button type="secondaryText" icon="first_page" disabled={current_page === 1} onClick={() => onChange(1)} />
      <Button type="secondaryText" icon="chevron_left" disabled={current_page === 1} onClick={() => onChange(current_page - 1)} />
      <span>Page {current_page} of {num_pages}</span>
      <Button type="secondaryText" icon="chevron_right" disabled={current_page === num_pages} onClick={() => onChange(current_page + 1)} />
      <Button type="secondaryText" icon="last_page" disabled={current_page === num_pages} onClick={() => onChange(num_pages)} />
    </div>
  );
}

/** at-table-actions — toolbar above a search table: search, filter, column manager, export, custom actions. */
export function TableActions({ search, onSearch, placeholder = "Search", columns, hidden = [], onColumnsChange, filters, actions, onExport }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 8, flexWrap: "wrap", padding: "8px 0" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Search placeholder={placeholder} value={search} onChange={onSearch} />
        {filters}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {actions}
        {columns && <ColumnManager columns={columns} hidden={hidden} onChange={onColumnsChange} />}
        {onExport && <Menu align="end" trigger={<Button type="secondaryText" icon="download" title="Export" />} items={[{ label: "Export CSV", onClick: () => onExport("csv") }, { label: "Export Excel", onClick: () => onExport("xlsx") }]} />}
      </div>
    </div>
  );
}

/** at-column-manager — show/hide columns menu. */
export function ColumnManager({ columns = [], hidden = [], onChange }) {
  return (
    <Menu align="end" autoclose={false} width={220} trigger={<Button type="secondaryText" icon="column" title="Columns" />}>
      <div style={{ padding: "4px 8px", fontSize: "var(--token-font-size-xs)", fontWeight: "var(--token-font-weight-med)", color: "var(--token-text-muted)" }}>Columns</div>
      {columns.map((c) => <Checkbox key={c.field} label={c.header} checked={!hidden.includes(c.field)} onChange={() => onChange && onChange(hidden.includes(c.field) ? hidden.filter((x) => x !== c.field) : [...hidden, c.field])} />)}
    </Menu>
  );
}

/** at-table-filter-menu — "Filter" button opening per-column checkbox filters; active filters show as a count. */
export function TableFilterMenu({ filters = [], value = {}, onChange }) {
  const count = Object.values(value).reduce((a, v) => a + v.length, 0);
  return (
    <Menu autoclose={false} width={240} trigger={<Button type="secondaryOutline" icon="filter" label={count ? `Filters (${count})` : "Filters"} />}>
      {filters.map((f) => (
        <div key={f.field} style={{ display: "flex", flexDirection: "column", gap: 2, paddingBottom: 4 }}>
          <div style={{ padding: "4px 8px", fontSize: "var(--token-font-size-xs)", fontWeight: "var(--token-font-weight-med)", color: "var(--token-text-muted)" }}>{f.header}</div>
          {f.options.map((o) => { const cur = value[f.field] || []; return <Checkbox key={o} label={o} checked={cur.includes(o)} onChange={() => onChange({ ...value, [f.field]: cur.includes(o) ? cur.filter((x) => x !== o) : [...cur, o] })} />; })}
        </div>
      ))}
    </Menu>
  );
}
