import React from "react";


const hoverBg = "color-mix(in srgb, var(--token-surface-overlay) 10%, transparent)";

/** at-select-option — row in a Select / MultiSelect listbox. */
export function SelectOption({ value, label, is_active, disabled, onClick, before, after }) {
  const [h, setH] = React.useState(false);
  return (
    <li role="option" aria-selected={!!is_active} onClick={disabled ? undefined : onClick} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{ display: "flex", alignItems: "center", gap: 4, padding: 8, borderRadius: "var(--token-menu-item-radius)", fontSize: "var(--token-font-size-body)", cursor: disabled ? "default" : "pointer", opacity: disabled ? 0.5 : 1,
        background: is_active ? "var(--token-state-active-background)" : h ? hoverBg : "transparent", color: is_active ? "var(--token-state-active-foreground)" : disabled ? "var(--token-state-disabled-foreground)" : undefined, transition: "background-color 150ms" }}>
      {before}
      <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{label ?? value}</span>
      {after}
    </li>
  );
}
