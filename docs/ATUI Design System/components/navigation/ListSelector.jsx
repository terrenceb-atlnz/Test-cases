import React from "react";
import { Icon } from "../core/Icon.jsx";

const hoverBg = "color-mix(in srgb, var(--token-surface-overlay) 10%, transparent)";

/** at-list-selector / -item — selectable navigation list with title + subtitle rows. */
export function ListSelector({ options = [], selected, onSelect, style }) {
  const [sel, setSel] = React.useState(selected ?? options[0]?.id);
  return (
    <div role="listbox" style={{ display: "flex", flexDirection: "column", gap: 2, ...style }}>
      {options.map((o) => <ListSelectorItem key={o.id} {...o} is_active={sel === o.id} onClick={() => { setSel(o.id); onSelect && onSelect(o.id); }} />)}
    </div>
  );
}

export function ListSelectorItem({ title, subtitle, icon, is_active, onClick, after }) {
  const [h, setH] = React.useState(false);
  return (
    <div role="option" aria-selected={!!is_active} tabIndex={0} onClick={onClick} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{ display: "flex", alignItems: "center", gap: 8, padding: 8, borderRadius: "var(--token-menu-item-radius)", cursor: "pointer", background: is_active ? "var(--token-state-active-background)" : h ? hoverBg : "transparent", color: is_active ? "var(--token-state-active-foreground)" : undefined, transition: "background-color 150ms" }}>
      {icon && <Icon name={icon} />}
      <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
        <span style={{ fontWeight: "var(--token-font-weight-med)" }}>{title}</span>
        {subtitle && <span style={{ fontSize: "var(--token-font-size-sm)", color: is_active ? "inherit" : "var(--token-text-muted)" }}>{subtitle}</span>}
      </div>
      {after}
    </div>
  );
}
